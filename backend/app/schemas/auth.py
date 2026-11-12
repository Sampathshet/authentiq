from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def validate_password_strength(password: str) -> str:
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters long")
    checks = [
        any(c.islower() for c in password),
        any(c.isupper() for c in password),
        any(c.isdigit() for c in password),
        any(not c.isalnum() for c in password),
    ]
    if sum(checks) < 3:
        raise ValueError("Password must include at least three of: lowercase, uppercase, number, symbol")
    return password


class RegisterRequest(StrictModel):
    display_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str
    confirm_password: str
    account_type: Literal["individual", "organization"] = "individual"
    organization_name: str | None = Field(default=None, max_length=160)
    accept_terms: bool

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @field_validator("display_name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Display name is required")
        return value

    @model_validator(mode="after")
    def validate_registration(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        if not self.accept_terms:
            raise ValueError("You must accept the terms to create an account")
        if self.account_type == "organization" and not (self.organization_name or "").strip():
            raise ValueError("Organization name is required for organization accounts")
        return self


class LoginRequest(StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)
    remember_me: bool = False


class RefreshRequest(StrictModel):
    refresh_token: str = Field(min_length=20)


class LogoutRequest(StrictModel):
    refresh_token: str | None = None


class ForgotPasswordRequest(StrictModel):
    email: EmailStr


class ResetPasswordRequest(StrictModel):
    token: str = Field(min_length=20)
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @model_validator(mode="after")
    def match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class ChangePasswordRequest(StrictModel):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @model_validator(mode="after")
    def match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        if self.current_password == self.new_password:
            raise ValueError("New password must differ from the current password")
        return self


class ProfileUpdateRequest(StrictModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    avatar_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    theme: Literal["dark", "light", "system"] | None = None


class UserOut(BaseModel):
    id: str
    email: EmailStr
    display_name: str
    account_type: str
    role: str
    organization_id: str | None = None
    organization_name: str | None = None
    avatar_color: str
    is_demo: bool
    created_at: datetime
    last_login_at: datetime | None = None


class SessionOut(BaseModel):
    id: str
    user_agent: str | None
    ip_address: str | None
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None
    current: bool = False


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class MessageResponse(BaseModel):
    message: str
    detail: str | None = None
