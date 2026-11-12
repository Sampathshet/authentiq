import json

from sqlalchemy import select

from app.core.database import SessionLocal, init_db
from app.models import User
from app.security.passwords import hash_password

DEMO_PASSWORD = "Authentiq!Demo2026"
DEMO_VERIFIER_PASSWORD = "Authentiq!Verify2026"
DEMO_TEAM_PASSWORD = "Authentiq!Team2026"
ADMIN_PASSWORD = "Authentiq!Admin2026"
DEMO_EMAIL = "demo@authentiq.dev"
DEMO_VERIFIER_EMAIL = "verifier@authentiq.dev"
DEMO_TEAM_EMAIL = "maya@authentiq.dev"
ADMIN_EMAIL = "admin@authentiq.dev"

DEMO_ACCOUNTS = (
    {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
        "display_name": "Site Administrator",
        "role": "site_admin",
        "account_type": "individual",
        "avatar_color": "#454545",
    },
    {
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD,
        "display_name": "Ava Sterling",
        "role": "org_admin",
        "account_type": "organization",
        "avatar_color": "#171717",
    },
    {
        "email": DEMO_VERIFIER_EMAIL,
        "password": DEMO_VERIFIER_PASSWORD,
        "display_name": "Priya Raman",
        "role": "verifier",
        "account_type": "individual",
        "avatar_color": "#454545",
    },
    {
        "email": DEMO_TEAM_EMAIL,
        "password": DEMO_TEAM_PASSWORD,
        "display_name": "Maya Chen",
        "role": "creator",
        "account_type": "individual",
        "avatar_color": "#D0D0D0",
    },
)


def seed_demo_data() -> None:
    init_db()
    db = SessionLocal()
    try:
        created = []
        for account in DEMO_ACCOUNTS:
            existing = db.execute(select(User).where(User.email == account["email"])).scalar_one_or_none()
            if existing:
                continue
            user = User(
                email=account["email"],
                password_hash=hash_password(account["password"]),
                display_name=account["display_name"],
                account_type=account["account_type"],
                role=account["role"],
                avatar_color=account["avatar_color"],
                is_demo=True,
                last_login_at=None,
            )
            db.add(user)
            created.append(account["email"])
        db.commit()
        print(json.dumps({"created_accounts": created, "accounts": [account["email"] for account in DEMO_ACCOUNTS]}, indent=2))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
