import uuid
from datetime import datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)


def _password_rules(v: str) -> str:
    if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one letter and one number.")
    return v


# Postgres INET columns come back as ipaddress objects; the API returns plain strings.
IPStr = Annotated[str | None, BeforeValidator(lambda v: str(v) if v is not None else None)]

Password = Annotated[str, Field(min_length=10, max_length=128), AfterValidator(_password_rules)]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: Password
    display_name: str = Field(min_length=1, max_length=80)
    is_minor: bool
    guardian_email: EmailStr | None = None
    accept_terms: bool

    @model_validator(mode="after")
    def _password_not_email(self):
        if self.password.lower() == str(self.email).lower():
            raise ValueError("Password can't be the same as your email.")
        return self


class RegisterResponse(BaseModel):
    user_id: uuid.UUID
    status: str
    message: str


class EmailRequest(BaseModel):
    email: EmailStr


class TokenRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    new_password: Password


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: Password


class AuthUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    status: str
    roles: list[str]
    permissions: list[str]
    display_name: str | None = None
    onboarding_completed: bool | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUser


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime
    user_agent: str | None
    ip_address: IPStr
    current: bool = False


class MessageResponse(BaseModel):
    message: str
