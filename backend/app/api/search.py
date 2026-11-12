from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Dispute, Idea, Registration, TeamMember, TeamProject, TheftAlert, User
from app.services.serializers import dispute_out, idea_out, registration_out

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(
    q: str = Query(min_length=2, max_length=120),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pattern = f"%{q.strip()}%"
    registrations = db.execute(
        select(Registration).where(
            Registration.user_id == user.id,
            or_(
                Registration.title.ilike(pattern),
                Registration.registration_id.ilike(pattern),
                Registration.sha256.ilike(pattern),
                Registration.file_name.ilike(pattern),
            ),
        ).limit(6)
    ).scalars().all()
    ideas = db.execute(
        select(Idea).where(Idea.user_id == user.id, or_(Idea.title.ilike(pattern), Idea.idea_ref.ilike(pattern))).limit(5)
    ).scalars().all()
    team_ids = set(db.execute(select(TeamMember.project_id).where(TeamMember.user_id == user.id)).scalars().all())
    teams = db.execute(
        select(TeamProject).where(
            or_(TeamProject.owner_id == user.id, TeamProject.id.in_(team_ids)),
            TeamProject.name.ilike(pattern),
        ).limit(5)
    ).scalars().all()
    disputes = db.execute(
        select(Dispute).where(
            or_(Dispute.claimant_id == user.id, Dispute.respondent_id == user.id),
            or_(Dispute.dispute_ref.ilike(pattern), Dispute.reason.ilike(pattern)),
        ).limit(5)
    ).scalars().all()
    alerts = db.execute(
        select(TheftAlert).where(TheftAlert.owner_id == user.id, TheftAlert.alert_type.ilike(pattern)).limit(5)
    ).scalars().all()
    return {
        "registrations": [registration_out(item) for item in registrations],
        "ideas": [idea_out(item) for item in ideas],
        "teams": [{"id": item.id, "name": item.name, "status": item.status} for item in teams],
        "disputes": [dispute_out(item) for item in disputes],
        "alerts": [{"id": item.id, "type": item.alert_type, "status": item.status, "created_at": item.created_at.isoformat()} for item in alerts],
        "total": len(registrations) + len(ideas) + len(teams) + len(disputes) + len(alerts),
    }
