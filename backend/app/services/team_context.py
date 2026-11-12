"""Team context for registrations.

A registration can be attributed to a team project. Team members then share
read access to that record, the record shows up on the team workspace, and the
public registry can credit the team instead of a single person.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OwnershipAllocation, Registration, TeamMember, TeamProject, User
from app.services.serializers import iso


def active_membership(db: Session, project_id: str, user) -> TeamMember | None:
    """The active membership row of a user inside a team project."""
    if not user or not getattr(user, "id", None):
        return None
    return db.execute(
        select(TeamMember).where(
            TeamMember.project_id == project_id,
            TeamMember.user_id == user.id,
            TeamMember.status == "active",
        )
    ).scalar_one_or_none()


def is_team_participant(db: Session, project_id: str, user) -> bool:
    """True when the user owns the project or is an active member of it."""
    if not user or not getattr(user, "id", None):
        return False
    project = db.get(TeamProject, project_id)
    if not project:
        return False
    if project.owner_id == user.id:
        return True
    return active_membership(db, project_id, user) is not None


def team_context(db: Session, registration: Registration) -> dict | None:
    """Ownership context for a team-attributed registration."""
    project_id = getattr(registration, "team_project_id", None)
    if not project_id:
        return None
    project = db.get(TeamProject, project_id)
    if not project:
        return None

    members = db.execute(
        select(TeamMember)
        .where(TeamMember.project_id == project.id, TeamMember.status == "active")
        .order_by(TeamMember.created_at.asc())
    ).scalars().all()
    approved = db.execute(
        select(OwnershipAllocation).where(
            OwnershipAllocation.project_id == project.id,
            OwnershipAllocation.status == "approved",
        )
    ).scalars().all()
    proposed = db.execute(
        select(OwnershipAllocation).where(
            OwnershipAllocation.project_id == project.id,
            OwnershipAllocation.status == "proposed",
        )
    ).scalars().all()

    approved_percent = {allocation.member_id: allocation.percent for allocation in approved}
    proposed_percent = {allocation.member_id: allocation.percent for allocation in proposed}
    if approved:
        allocation_status = "approved"
        allocation_total = round(sum(approved_percent.values()), 2)
    elif proposed:
        allocation_status = "proposed"
        allocation_total = round(sum(proposed_percent.values()), 2)
    else:
        allocation_status = None
        allocation_total = 0.0

    return {
        "id": project.id,
        "name": project.name,
        "status": project.status,
        "ledger_tx_id": project.ledger_tx_id,
        "allocation_status": allocation_status,
        "allocation_total": allocation_total,
        "members": [
            {
                "id": member.id,
                "name": member.display_name or member.email,
                "email": member.email,
                "role": member.role,
                "percent": approved_percent.get(
                    member.id, proposed_percent.get(member.id, 0.0)
                ),
                "ownership_percent": member.ownership_percent,
            }
            for member in members
        ],
    }


def team_creations(db: Session, project: TeamProject, limit: int = 50) -> list[dict]:
    """Registrations attributed to a team project."""
    registrations = db.execute(
        select(Registration)
        .where(Registration.team_project_id == project.id)
        .order_by(Registration.registered_at.desc())
        .limit(limit)
    ).scalars().all()
    if not registrations:
        return []

    owners = db.execute(
        select(User).where(User.id.in_({item.user_id for item in registrations}))
    ).scalars().all()
    owner_names = {owner.id: owner.display_name for owner in owners}

    return [
        {
            "id": registration.id,
            "registration_id": registration.registration_id,
            "title": registration.title,
            "asset_type": registration.asset_type,
            "privacy": registration.privacy,
            "status": registration.status,
            "sha256": registration.sha256,
            "registered_at": iso(registration.registered_at),
            "owner_id": registration.user_id,
            "owner_name": owner_names.get(registration.user_id),
        }
        for registration in registrations
    ]
