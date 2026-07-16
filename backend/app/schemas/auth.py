import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str
    phone: str | None = None
    role: UserRole = UserRole.customer
    city: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: uuid.UUID


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    phone: str | None
    full_name: str
    role: UserRole
    avatar_url: str | None
    city: str | None
    is_verified: bool
    wallet_balance: float

    model_config = {"from_attributes": True}
