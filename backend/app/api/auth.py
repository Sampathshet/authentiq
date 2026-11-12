import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import client_ip, get_current_user
from app.models import Organization, OrganizationMember, PasswordResetToken, User, UserSession
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionOut,
    TokenResponse,
    UserOut,
)
from app.security.crypto import sha256_text, utcnow
from app.security.passwords import hash_password, verify_password
from app.security.rate_limit import login_limiter, register_limiter
from app.security.tokens import (
    create_access_token,
    create_refresh_token,
    create_reset_token,
    decode_reset_token,
    hash_refresh_token,
)
from app.services.audit import append_audit
from app.services.notifications import notify

router = APIRouter(prefix="/auth", tags=["authentication"])

MAX_FAILED_LOGINS = 6
LOCK_MINUTES = 15


def _normalized_expiry(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _user_payload(db: Session, user: User) -> dict:
    payload = {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "account_type": user.account_type,
        "role": user.role,
        "organization_id": user.organization_id,
        "organization_name": None,
        "avatar_color": user.avatar_color,
        "is_demo": user.is_demo,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
    }
    if user.organization_id:
        org = db.get(Organization, user.organization_id)
        payload["organization_name"] = org.name if org else None
    return payload


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug or "org")[:140] + "-" + secrets.token_hex(4)


def _issue_session(db: Session, user: User, request: Request, remember_me: bool = False) -> TokenResponse:
    refresh_token, refresh_hash, refresh_seconds = create_refresh_token()
    if remember_me:
        refresh_seconds = 30 * 24 * 3600
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=refresh_hash,
        user_agent=(request.headers.get("user-agent") or "")[:400],
        ip_address=client_ip(request),
        expires_at=utcnow() + timedelta(seconds=refresh_seconds),
    )
    db.add(session)
    db.flush()
    access_token, expires_in = create_access_token(user.id, session.id, user.role, user.organization_id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=UserOut.model_validate(_user_payload(db, user)),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    allowed, retry_after = register_limiter.check(f"register:{ip}", 10, 3600)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many registration attempts. Retry in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
    email = payload.email.lower().strip()
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
        account_type=payload.account_type,
        role="creator",
        avatar_color=secrets.choice(["#171717", "#B7FF00", "#454545", "#888888", "#D0D0D0", "#EAEAEA"]),
    )
    db.add(user)
    db.flush()

    if payload.account_type == "organization":
        organization = Organization(
            name=(payload.organization_name or f"{user.display_name} Organization").strip(),
            slug=_slugify(payload.organization_name or user.display_name),
            owner_id=user.id,
        )
        db.add(organization)
        db.flush()
        user.organization_id = organization.id
        user.role = "org_admin"
        db.add(
            OrganizationMember(
                organization_id=organization.id,
                user_id=user.id,
                role="org_admin",
                status="active",
            )
        )

    append_audit(
        db,
        "account_created",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="user",
        entity_id=user.id,
        metadata={"account_type": user.account_type, "role": user.role},
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
    )
    notify(
        db,
        user.id,
        "account",
        "Welcome to AUTHENTIQ",
        "Your workspace is ready. Register your first creation to generate a cryptographic ownership record.",
        "user",
        user.id,
    )

    response = _issue_session(db, user, request, payload.account_type == "organization")
    db.commit()
    return response


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    email = payload.email.lower().strip()
    allowed, retry_after = login_limiter.check(f"login:{ip}:{email}", settings.login_rate_limit, settings.login_rate_window_seconds)
    if not allowed:
        append_audit(
            db,
            "login_rate_limited",
            actor_ref=email,
            metadata={"ip": ip},
            ip_address=ip,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Retry in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if user.locked_until and _normalized_expiry(user.locked_until) > utcnow():
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account temporarily locked after repeated failed logins")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    if not verify_password(payload.password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_LOGINS:
            user.locked_until = utcnow() + timedelta(minutes=LOCK_MINUTES)
            user.failed_login_count = 0
        append_audit(
            db,
            "login_failed",
            actor_id=user.id,
            actor_ref=user.email,
            metadata={"ip": ip},
            ip_address=ip,
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    previous_agents = db.execute(
        select(UserSession.user_agent).where(UserSession.user_id == user.id).limit(20)
    ).scalars().all()
    current_agent = (request.headers.get("user-agent") or "")[:400]
    new_device = bool(previous_agents) and current_agent not in previous_agents

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = utcnow()
    response = _issue_session(db, user, request, payload.remember_me)
    if new_device:
        notify(
            db,
            user.id,
            "security",
            "New device sign-in",
            f"A new sign-in to your AUTHENTIQ account was detected from {ip}.",
            "session",
            user.id,
        )
    append_audit(
        db,
        "user_logged_in",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="session",
        entity_id=user.id,
        metadata={"ip": ip, "new_device": new_device},
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return response


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    token_hash = hash_refresh_token(payload.refresh_token)
    session = db.execute(select(UserSession).where(UserSession.refresh_token_hash == token_hash)).scalar_one_or_none()
    if not session or session.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is invalid or revoked")
    if _normalized_expiry(session.expires_at) < utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")
    user = db.get(User, session.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    new_refresh, new_hash, refresh_seconds = create_refresh_token()
    session.refresh_token_hash = new_hash
    session.last_used_at = utcnow()
    session.expires_at = utcnow() + timedelta(seconds=refresh_seconds)
    access_token, expires_in = create_access_token(user.id, session.id, user.role, user.organization_id)
    db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=expires_in,
        user=UserOut.model_validate(_user_payload(db, user)),
    )


@router.post("/logout", response_model=MessageResponse)
def logout(payload: LogoutRequest, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    revoked = False
    if payload.refresh_token:
        session = db.execute(
            select(UserSession).where(UserSession.refresh_token_hash == hash_refresh_token(payload.refresh_token))
        ).scalar_one_or_none()
        if session and session.user_id == user.id:
            session.revoked_at = utcnow()
            revoked = True
    else:
        sessions = db.execute(
            select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        ).scalars().all()
        for session in sessions:
            session.revoked_at = utcnow()
        revoked = True
    append_audit(
        db,
        "user_logged_out",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="session",
        entity_id=user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return MessageResponse(message="Logged out" if revoked else "No active session found")


@router.get("/me", response_model=UserOut)
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return UserOut.model_validate(_user_payload(db, user))


@router.patch("/me", response_model=UserOut)
def update_me(payload: ProfileUpdateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.avatar_color is not None:
        user.avatar_color = payload.avatar_color
    append_audit(db, "profile_updated", actor_id=user.id, actor_ref=user.email, entity_type="user", entity_id=user.id)
    db.commit()
    return UserOut.model_validate(_user_payload(db, user))


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user:
        token = create_reset_token(user.id)
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=sha256_text(token),
                expires_at=utcnow() + timedelta(minutes=settings.reset_token_minutes),
            )
        )
        append_audit(
            db,
            "password_reset_requested",
            actor_id=user.id,
            actor_ref=user.email,
            metadata={"ip": client_ip(request)},
            ip_address=client_ip(request),
        )
        db.commit()
        if settings.environment != "production":
            return MessageResponse(
                message="Password reset token generated",
                detail=token,
            )
    else:
        db.commit()
    return MessageResponse(
        message="If an account exists for that email, reset instructions have been generated.",
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    try:
        decoded = decode_reset_token(payload.token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    token_hash = sha256_text(payload.token)
    record = db.execute(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)).scalar_one_or_none()
    if not record or record.used_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token has already been used or is invalid")
    if _normalized_expiry(record.expires_at) < utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token has expired")
    user = db.get(User, decoded["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.password_hash = hash_password(payload.new_password)
    record.used_at = utcnow()
    sessions = db.execute(select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))).scalars().all()
    for session in sessions:
        session.revoked_at = utcnow()
    append_audit(
        db,
        "password_reset_completed",
        actor_id=user.id,
        actor_ref=user.email,
        metadata={"ip": client_ip(request)},
        ip_address=client_ip(request),
    )
    db.commit()
    return MessageResponse(message="Password has been reset. Sign in with your new password.")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    sessions = db.execute(select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))).scalars().all()
    for session in sessions:
        session.revoked_at = utcnow()
    append_audit(
        db,
        "password_changed",
        actor_id=user.id,
        actor_ref=user.email,
        ip_address=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return MessageResponse(message="Password changed. All sessions have been signed out.")


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sessions = db.execute(
        select(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .order_by(UserSession.created_at.desc())
    ).scalars().all()
    return [
        SessionOut(
            id=session.id,
            user_agent=session.user_agent,
            ip_address=session.ip_address,
            created_at=session.created_at,
            expires_at=session.expires_at,
            last_used_at=session.last_used_at,
        )
        for session in sessions
    ]


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
def revoke_session(session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.get(UserSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session.revoked_at = utcnow()
    append_audit(db, "session_revoked", actor_id=user.id, actor_ref=user.email, entity_type="session", entity_id=session.id)
    db.commit()
    return MessageResponse(message="Session revoked")
