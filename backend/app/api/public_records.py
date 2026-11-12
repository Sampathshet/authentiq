"""Public records registry.

Only registrations whose owner explicitly chose the "Public record" disclosure
level (privacy == "public") are listed here. Private records and
"public fingerprint" records are never enumerated: they stay resolvable only
through their reference or a silent-sharing link.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Organization, Registration, TeamProject, User
from app.services.serializers import iso

router = APIRouter(prefix="/public", tags=["public records"])

PUBLIC_PRIVACY = "public"
DESCRIPTION_PREVIEW = 240


@router.get("/records")
def list_public_records(
    q: str | None = Query(default=None, max_length=120),
    asset_type: str | None = Query(default=None, max_length=40),
    sort: str = Query(default="recent", pattern="^(recent|oldest|title|creator)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=48),
    db: Session = Depends(get_db),
):
    """List and search the public records registry."""
    text = (q or "").strip()
    creator_filter = [Registration.privacy == PUBLIC_PRIVACY]
    if asset_type:
        creator_filter.append(Registration.asset_type == asset_type)

    joined = (
        select(Registration, User.display_name, Organization.name, TeamProject.name)
        .join(User, User.id == Registration.user_id)
        .outerjoin(Organization, Organization.id == Registration.organization_id)
        .outerjoin(TeamProject, TeamProject.id == Registration.team_project_id)
        .where(*creator_filter)
    )
    count_query = (
        select(func.count(Registration.id))
        .join(User, User.id == Registration.user_id)
        .outerjoin(TeamProject, TeamProject.id == Registration.team_project_id)
        .where(*creator_filter)
    )

    if text:
        pattern = f"%{text}%"
        search = or_(
            User.display_name.ilike(pattern),
            Registration.title.ilike(pattern),
            Registration.description.ilike(pattern),
            Registration.registration_id.ilike(pattern),
            cast(Registration.tags, String).ilike(pattern),
            TeamProject.name.ilike(pattern),
        )
        joined = joined.where(search)
        count_query = count_query.where(search)

    order = {
        "recent": Registration.registered_at.desc(),
        "oldest": Registration.registered_at.asc(),
        "title": Registration.title.asc(),
        "creator": User.display_name.asc(),
    }[sort]

    total = db.execute(count_query).scalar_one()
    rows = db.execute(
        joined.order_by(order).offset((page - 1) * page_size).limit(page_size)
    ).all()

    creator_count = db.execute(
        select(func.count(func.distinct(Registration.user_id))).where(
            Registration.privacy == PUBLIC_PRIVACY
        )
    ).scalar_one()
    latest = db.execute(
        select(func.max(Registration.registered_at)).where(Registration.privacy == PUBLIC_PRIVACY)
    ).scalar_one()
    facets = db.execute(
        select(Registration.asset_type, func.count(Registration.id))
        .where(Registration.privacy == PUBLIC_PRIVACY)
        .group_by(Registration.asset_type)
        .order_by(func.count(Registration.id).desc())
    ).all()

    items = []
    for registration, creator_name, organization_name, team_name in rows:
        description = registration.description or ""
        items.append(
            {
                "registration_reference": registration.registration_id,
                "title": registration.title,
                "description": description[:DESCRIPTION_PREVIEW] or None,
                "description_truncated": len(description) > DESCRIPTION_PREVIEW,
                "creator_name": creator_name,
                "organization": organization_name,
                "team_name": team_name,
                "asset_type": registration.asset_type,
                "tags": registration.tags or [],
                "fingerprint": registration.sha256,
                "commitment": registration.commitment,
                "status": registration.status,
                "verified_at": iso(registration.verified_at),
                "registered_at": iso(registration.registered_at),
                "creation_timestamp": iso(registration.creation_timestamp),
                "ledger_mode": registration.ledger_mode,
                "ledger_tx_id": registration.ledger_tx_id,
                "verify_path": f"/verify/{registration.registration_id}",
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
        "query": text or None,
        "sort": sort,
        "asset_type": asset_type,
        "total_creators": creator_count,
        "latest_registered_at": iso(latest),
        "asset_types": [{"value": value, "count": count} for value, count in facets],
        "privacy_note": (
            "Only records whose creator selected the Public record disclosure level are listed. "
            "Private and public-fingerprint records are never enumerated here, and the original "
            "file is never served."
        ),
    }
