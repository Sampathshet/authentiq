import json
import secrets
from datetime import timezone
from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.ledger import ledger_service
from app.models import (
    ContributionRecord,
    OwnershipAllocation,
    TeamMember,
    TeamProject,
    User,
)
from app.schemas.content import (
    AllocationApproveRequest,
    AllocationProposeRequest,
    ContributionCreateRequest,
    TeamCreateRequest,
    TeamInviteRequest,
    TeamJoinRequest,
)
from app.security.crypto import random_url_token, utcnow
from app.services.audit import append_audit
from app.services.notifications import notify
from app.services.serializers import allocation_out, team_member_out, team_out
from app.services.team_context import team_creations

router = APIRouter(prefix="/teams", tags=["team ownership"])


def _project_or_404(db: Session, project_id: str) -> TeamProject:
    project = db.get(TeamProject, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team project not found")
    return project


def _active_member(db: Session, project_id: str, user: User) -> TeamMember | None:
    return db.execute(
        select(TeamMember).where(
            TeamMember.project_id == project_id,
            TeamMember.user_id == user.id,
            TeamMember.status == "active",
        )
    ).scalar_one_or_none()


def _require_member(db: Session, project: TeamProject, user: User) -> TeamMember:
    if project.owner_id == user.id:
        member = _active_member(db, project.id, user)
        if member:
            return member
    member = _active_member(db, project.id, user)
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not an active member of this team")
    return member


def _can_manage(project: TeamProject, member: TeamMember | None, user: User) -> bool:
    return project.owner_id == user.id or (member is not None and member.role in {"co_owner", "owner"})


def _detail(db: Session, project: TeamProject, user: User) -> dict:
    members = db.execute(
        select(TeamMember).where(TeamMember.project_id == project.id).order_by(TeamMember.created_at.asc())
    ).scalars().all()
    contributions = db.execute(
        select(ContributionRecord, TeamMember)
        .join(TeamMember, ContributionRecord.member_id == TeamMember.id)
        .where(ContributionRecord.project_id == project.id)
        .order_by(ContributionRecord.created_at.desc())
    ).all()
    allocations = db.execute(
        select(OwnershipAllocation, TeamMember)
        .join(TeamMember, OwnershipAllocation.member_id == TeamMember.id)
        .where(OwnershipAllocation.project_id == project.id)
        .order_by(OwnershipAllocation.created_at.desc(), OwnershipAllocation.percent.desc())
    ).all()
    owner = db.get(User, project.owner_id)
    membership = _active_member(db, project.id, user)
    invited = db.execute(
        select(TeamMember).where(
            TeamMember.project_id == project.id,
            TeamMember.user_id == user.id,
            TeamMember.status == "invited",
        )
    ).scalar_one_or_none()
    if invited is None:
        invited = db.execute(
            select(TeamMember).where(
                TeamMember.project_id == project.id,
                TeamMember.email == user.email,
                TeamMember.status == "invited",
            )
        ).scalar_one_or_none()
    payload = team_out(
        project,
        members,
        owner.display_name if owner else None,
        membership.role if membership else (invited.role if invited else ("owner" if project.owner_id == user.id else None)),
        membership.status if membership else (invited.status if invited else ("owner" if project.owner_id == user.id else None)),
    )
    payload["can_manage"] = _can_manage(project, membership, user)
    payload["creations"] = team_creations(db, project)
    payload["contributions"] = [
        {
            "id": record.id,
            "member_id": record.member_id,
            "member_name": member.display_name or member.email,
            "description": record.description,
            "file_reference": record.file_reference,
            "status": record.status,
            "approved_at": record.approved_at.isoformat() if record.approved_at else None,
            "created_at": record.created_at.isoformat(),
        }
        for record, member in contributions
    ]
    latest_by_member = {}
    for allocation, member in allocations:
        latest_by_member.setdefault(allocation.member_id, allocation_out(allocation, member))
    payload["allocations"] = list(latest_by_member.values())
    payload["allocation_total"] = round(sum(item["percent"] for item in payload["allocations"] if item["status"] == "proposed"), 2)
    payload["timeline"] = sorted(
        [
            {
                "type": "member_joined",
                "label": f"{member.display_name or member.email} joined the project",
                "timestamp": (member.joined_at or member.created_at).isoformat(),
            }
            for member in members
            if member.status == "active"
        ]
        + [
            {
                "type": "contribution",
                "label": f"{member.display_name or member.email} submitted a contribution",
                "timestamp": record.created_at.isoformat(),
            }
            for record, member in contributions
        ]
        + [
            {
                "type": "ownership",
                "label": f"Ownership allocation proposed at {allocation.percent}%",
                "timestamp": allocation.created_at.isoformat(),
            }
            for allocation, _ in allocations
            if allocation.status == "proposed"
        ],
        key=lambda item: item["timestamp"],
        reverse=True,
    )
    return payload


@router.post("", status_code=status.HTTP_201_CREATED)
def create_team(
    payload: TeamCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = TeamProject(
        name=payload.name,
        description=payload.description,
        owner_id=user.id,
        organization_id=user.organization_id,
        is_demo=user.is_demo,
    )
    db.add(project)
    db.flush()
    owner_member = TeamMember(
        project_id=project.id,
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role="owner",
        status="active",
        joined_at=utcnow(),
        invited_by=user.id,
        ownership_percent=100.0,
    )
    db.add(owner_member)
    append_audit(
        db,
        "team_project_created",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="team_project",
        entity_id=project.id,
        metadata={"name": project.name},
    )
    db.commit()
    return _detail(db, project, user)


@router.get("")
def list_teams(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    member_project_ids = set(
        db.execute(select(TeamMember.project_id).where(TeamMember.user_id == user.id)).scalars().all()
    )
    invited_project_ids = set(
        db.execute(
            select(TeamMember.project_id).where(
                TeamMember.email == user.email,
                TeamMember.status == "invited",
            )
        ).scalars().all()
    )
    project_ids = member_project_ids | invited_project_ids
    projects = db.execute(
        select(TeamProject).where(or_(TeamProject.id.in_(project_ids), TeamProject.owner_id == user.id)).order_by(TeamProject.created_at.desc())
    ).scalars().all() if project_ids else db.execute(
        select(TeamProject).where(TeamProject.owner_id == user.id).order_by(TeamProject.created_at.desc())
    ).scalars().all()
    result = []
    for project in projects:
        members = db.execute(select(TeamMember).where(TeamMember.project_id == project.id)).scalars().all()
        membership = next((member for member in members if member.user_id == user.id), None)
        if membership is None:
            membership = next((member for member in members if member.email == user.email and member.status == "invited"), None)
        owner = db.get(User, project.owner_id)
        result.append(
            team_out(
                project,
                members,
                owner.display_name if owner else None,
                membership.role if membership else (("owner") if project.owner_id == user.id else None),
                membership.status if membership else ("owner" if project.owner_id == user.id else None),
            )
        )
    return {"items": result}


@router.get("/{project_id}")
def get_team(
    project_id: str,
    invite: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _project_or_404(db, project_id)
    if project.owner_id != user.id and not _active_member(db, project.id, user):
        invited = db.execute(
            select(TeamMember).where(
                TeamMember.project_id == project.id,
                TeamMember.user_id == user.id,
                TeamMember.status == "invited",
            )
        ).scalar_one_or_none()
        if invited is None:
            invited = db.execute(
                select(TeamMember).where(
                    TeamMember.project_id == project.id,
                    TeamMember.email == user.email,
                    TeamMember.status == "invited",
                )
            ).scalar_one_or_none()
        token_match = None
        if invite:
            token_match = db.execute(
                select(TeamMember).where(
                    TeamMember.project_id == project.id,
                    TeamMember.invite_token == invite.strip(),
                    TeamMember.status == "invited",
                )
            ).scalar_one_or_none()
        if not invited and not token_match:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not an active member of this team")
    return _detail(db, project, user)


@router.post("/{project_id}/invite", status_code=status.HTTP_201_CREATED)
def invite_member(
    project_id: str,
    payload: TeamInviteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _project_or_404(db, project_id)
    membership = _active_member(db, project.id, user)
    if not _can_manage(project, membership, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner or a co-owner can invite members")
    try:
        normalized = validate_email(payload.email, check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    existing = db.execute(
        select(TeamMember).where(TeamMember.project_id == project.id, TeamMember.email == normalized)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This email is already part of the team project")
    invited_user = db.execute(select(User).where(User.email == normalized)).scalar_one_or_none()
    member = TeamMember(
        project_id=project.id,
        user_id=invited_user.id if invited_user else None,
        email=normalized,
        display_name=payload.display_name or (invited_user.display_name if invited_user else normalized.split("@")[0]),
        role=payload.role,
        status="invited",
        invite_token=random_url_token(24),
        invited_by=user.id,
    )
    db.add(member)
    db.flush()
    append_audit(
        db,
        "team_member_invited",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="team_project",
        entity_id=project.id,
        metadata={"email": normalized, "role": payload.role},
    )
    if invited_user:
        notify(
            db,
            invited_user.id,
            "team_invitation",
            "Team invitation",
            f"You were invited to {project.name} as {payload.role}.",
            "team_project",
            project.id,
        )
    db.commit()
    return {
        "member": team_member_out(member),
        "invite_token": member.invite_token,
        "invite_url": f"/teams/{project.id}?invite={member.invite_token}",
        "delivery": "In-app notification created. Email delivery is not configured in this environment.",
    }


@router.post("/redeem")
def redeem_invitation(
    payload: TeamJoinRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    token = (payload.token or "").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invitation code is required")
    member = db.execute(
        select(TeamMember).where(TeamMember.invite_token == token, TeamMember.status == "invited")
    ).scalars().first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation code not found or already used")
    return _accept_invitation(db, member, user)


def _accept_invitation(db: Session, member: TeamMember, user: User) -> dict:
    project = _project_or_404(db, member.project_id)
    if member.status == "active":
        if member.user_id and member.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This invitation has already been accepted by another account")
        return {"message": "Already a member", "member": team_member_out(member), "project_id": project.id, "project_name": project.name}
    if member.user_id and member.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation was issued to another account. Sign in with the invited email address.",
        )
    if member.email != user.email:
        existing = db.execute(
            select(TeamMember).where(
                TeamMember.project_id == project.id,
                TeamMember.email == user.email,
                TeamMember.id != member.id,
            )
        ).scalars().first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This email is already part of the team project")
        invited_email = member.email
        member.email = user.email
        member.display_name = member.display_name or user.display_name
    else:
        invited_email = member.email
    member.user_id = user.id
    member.status = "active"
    member.joined_at = utcnow()
    member.invite_token = None
    append_audit(
        db,
        "team_invitation_accepted",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="team_project",
        entity_id=project.id,
        metadata={"member_id": member.id, "role": member.role, "invited_email": invited_email, "joined_email": user.email},
    )
    notify(
        db,
        project.owner_id,
        "team",
        "Team invitation accepted",
        f"{user.display_name} joined {project.name}.",
        "team_project",
        project.id,
    )
    db.commit()
    db.refresh(member)
    return {
        "message": "Invitation accepted",
        "member": team_member_out(member),
        "project_id": project.id,
        "project_name": project.name,
    }


@router.post("/{project_id}/join")
def join_team(
    project_id: str,
    payload: TeamJoinRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _project_or_404(db, project_id)
    member = None
    if payload.token:
        member = db.execute(
            select(TeamMember).where(
                TeamMember.project_id == project.id,
                TeamMember.invite_token == payload.token,
            )
        ).scalar_one_or_none()
    if member is None:
        member = db.execute(
            select(TeamMember).where(
                TeamMember.project_id == project.id,
                TeamMember.email == user.email,
                TeamMember.status == "invited",
            )
        ).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    return _accept_invitation(db, member, user)


@router.post("/{project_id}/contributions", status_code=status.HTTP_201_CREATED)
def add_contribution(
    project_id: str,
    payload: ContributionCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _project_or_404(db, project_id)
    member = _require_member(db, project, user)
    record = ContributionRecord(
        project_id=project.id,
        member_id=member.id,
        description=payload.description,
        file_reference=payload.file_reference,
        status="submitted",
    )
    db.add(record)
    db.flush()
    append_audit(
        db,
        "contribution_submitted",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="team_project",
        entity_id=project.id,
        metadata={"contribution_id": record.id},
    )
    notify(
        db,
        project.owner_id,
        "contribution",
        "Contribution submitted",
        f"{user.display_name} submitted a contribution to {project.name}.",
        "team_project",
        project.id,
    )
    db.commit()
    return {
        "id": record.id,
        "status": record.status,
        "created_at": record.created_at.isoformat(),
    }


@router.patch("/{project_id}/contributions/{contribution_id}/approve")
def approve_contribution(
    project_id: str,
    contribution_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _project_or_404(db, project_id)
    membership = _active_member(db, project.id, user)
    if not _can_manage(project, membership, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner or a co-owner can approve contributions")
    record = db.get(ContributionRecord, contribution_id)
    if not record or record.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contribution not found")
    record.status = "approved"
    record.approved_by = user.id
    record.approved_at = utcnow()
    member = db.get(TeamMember, record.member_id)
    if member and member.user_id:
        notify(
            db,
            member.user_id,
            "contribution",
            "Contribution approved",
            f"Your contribution to {project.name} was approved.",
            "team_project",
            project.id,
        )
    append_audit(
        db,
        "contribution_approved",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="team_project",
        entity_id=project.id,
        metadata={"contribution_id": record.id},
    )
    db.commit()
    return {"message": "Contribution approved"}


@router.post("/{project_id}/ownership/propose")
def propose_allocation(
    project_id: str,
    payload: AllocationProposeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _project_or_404(db, project_id)
    if project.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the project owner can propose an allocation")
    members = db.execute(
        select(TeamMember).where(TeamMember.project_id == project.id, TeamMember.status == "active")
    ).scalars().all()
    member_map = {member.id: member for member in members}
    seen = set()
    total = 0.0
    for item in payload.allocations:
        if item.member_id not in member_map:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Allocation references an inactive member")
        if item.member_id in seen:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Duplicate member allocation")
        seen.add(item.member_id)
        total += item.percent
    total = round(total, 6)
    if abs(total - 100.0) > 0.0001:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Ownership percentages must total exactly 100%. Current total: {total}%")
    missing = set(member_map) - seen
    if missing:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Every active member must receive an allocation, including 0% if intended")
    previous = db.execute(
        select(OwnershipAllocation).where(
            OwnershipAllocation.project_id == project.id,
            OwnershipAllocation.status == "proposed",
        )
    ).scalars().all()
    for allocation in previous:
        allocation.status = "superseded"
    created = []
    for item in payload.allocations:
        allocation = OwnershipAllocation(
            project_id=project.id,
            member_id=item.member_id,
            percent=round(item.percent, 4),
            status="proposed",
            proposed_by=user.id,
            approvals=[user.id],
        )
        db.add(allocation)
        created.append(allocation)
    append_audit(
        db,
        "ownership_allocation_proposed",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="team_project",
        entity_id=project.id,
        metadata={"total": total, "allocations": len(created)},
    )
    for member in members:
        if member.user_id and member.user_id != user.id:
            notify(
                db,
                member.user_id,
                "ownership",
                "Ownership allocation proposed",
                f"Review and approve your ownership percentage in {project.name}.",
                "team_project",
                project.id,
            )
    db.commit()
    return {"message": "Allocation proposed. Every member must approve.", "allocations": len(created), "total": total}


@router.post("/{project_id}/ownership/approve")
def approve_allocation(
    project_id: str,
    payload: AllocationApproveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _project_or_404(db, project_id)
    member = _require_member(db, project, user)
    allocations = db.execute(
        select(OwnershipAllocation).where(
            OwnershipAllocation.project_id == project.id,
            OwnershipAllocation.status == "proposed",
        )
    ).scalars().all()
    if not allocations:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No proposed allocation found")
    own = [allocation for allocation in allocations if allocation.member_id == member.id]
    if not own:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your member record has no allocation in this proposal")
    for allocation in own:
        approvals = list(allocation.approvals or [])
        if user.id not in approvals:
            approvals.append(user.id)
        allocation.approvals = approvals
    active_members = db.execute(
        select(TeamMember).where(TeamMember.project_id == project.id, TeamMember.status == "active")
    ).scalars().all()
    fully_approved = True
    for active in active_members:
        line = next((allocation for allocation in allocations if allocation.member_id == active.id), None)
        if not line or not active.user_id or active.user_id not in (line.approvals or []):
            fully_approved = False
            break
    if fully_approved:
        for allocation in allocations:
            allocation.status = "approved"
            allocation.approved_at = utcnow()
        for allocation in allocations:
            line_member = db.get(TeamMember, allocation.member_id)
            if line_member:
                line_member.ownership_percent = allocation.percent
        tx = ledger_service.record_team_ownership(
            db,
            user.id,
            project,
            [
                {
                    "member_id": allocation.member_id,
                    "percent": allocation.percent,
                }
                for allocation in allocations
            ],
        )
        project.ledger_tx_id = tx.tx_id
        project.status = "ownership_approved"
        append_audit(
            db,
            "ownership_allocation_approved",
            actor_id=user.id,
            actor_ref=user.email,
            entity_type="team_project",
            entity_id=project.id,
            metadata={"ledger_tx_id": tx.tx_id, "member_count": len(allocations)},
        )
        for active in active_members:
            if active.user_id:
                notify(
                    db,
                    active.user_id,
                    "ownership",
                    "Ownership allocation approved",
                    f"The ownership split for {project.name} is finalized and recorded in the ledger.",
                    "team_project",
                    project.id,
                )
    db.commit()
    return {
        "approved": fully_approved,
        "message": "Ownership allocation finalized" if fully_approved else "Your approval was recorded. Waiting for other members.",
        "ledger_tx_id": project.ledger_tx_id,
    }


@router.get("/{project_id}/ownership")
def get_ownership(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = _project_or_404(db, project_id)
    _require_member(db, project, user)
    allocations = db.execute(
        select(OwnershipAllocation, TeamMember)
        .join(TeamMember, OwnershipAllocation.member_id == TeamMember.id)
        .where(OwnershipAllocation.project_id == project.id)
        .order_by(OwnershipAllocation.created_at.desc())
    ).all()
    active = db.execute(
        select(TeamMember).where(TeamMember.project_id == project.id, TeamMember.status == "active")
    ).scalars().all()
    return {
        "allocations": [allocation_out(allocation, member) for allocation, member in allocations],
        "active_members": [team_member_out(member) for member in active],
        "ledger_tx_id": project.ledger_tx_id,
        "status": project.status,
    }


@router.get("/{project_id}/certificate")
def team_certificate(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = _project_or_404(db, project_id)
    _require_member(db, project, user)
    if project.status != "ownership_approved":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ownership certificate is available only after unanimous approval")
    allocations = db.execute(
        select(OwnershipAllocation, TeamMember)
        .join(TeamMember, OwnershipAllocation.member_id == TeamMember.id)
        .where(OwnershipAllocation.project_id == project.id, OwnershipAllocation.status == "approved")
        .order_by(OwnershipAllocation.percent.desc())
    ).all()
    ledger_record = ledger_service.verify_record(project.ledger_tx_id) if project.ledger_tx_id else None
    evidence = {
        "format": "AUTHENTIQ-TEAM-OWNERSHIP-CERTIFICATE-V1",
        "project": project.name,
        "project_id": project.id,
        "status": project.status,
        "ledger_mode": "simulation" if (ledger_record or {}).get("mode") == "simulation" else "polygon",
        "ledger_tx_id": project.ledger_tx_id,
        "ledger_record": ledger_record,
        "allocations": [
            {
                "member": member.display_name or member.email,
                "role": member.role,
                "percent": allocation.percent,
                "approvals": allocation.approvals or [],
                "approved_at": allocation.approved_at.isoformat() if allocation.approved_at else None,
            }
            for allocation, member in allocations
        ],
        "total_percent": round(sum(allocation.percent for allocation, _ in allocations), 4),
        "issued_at": utcnow().isoformat(),
        "note": "This certificate reflects the recorded team agreement. It is not a legal determination of copyright ownership.",
    }
    append_audit(
        db,
        "team_ownership_certificate_downloaded",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="team_project",
        entity_id=project.id,
    )
    db.commit()
    return Response(
        content=json.dumps(evidence, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="AUTHENTIQ-{project.name[:40].replace(" ", "-")}-ownership.json"'},
    )
