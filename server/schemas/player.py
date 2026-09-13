from __future__ import annotations

from pydantic import BaseModel, Field


class PlayerPublic(BaseModel):
    id: int
    handle: str
    email: str | None = None
    city: str
    wallet_credits: int
    bio: str
    created_at: str
    visit_count: int = 0
    stacks: list[dict] = []


class RegisterBody(BaseModel):
    handle: str = Field(min_length=2, max_length=32, pattern=r"^[^\s]{2,32}$")
    password: str = Field(min_length=8, max_length=128)
    email: str | None = Field(default=None, max_length=254)


class LoginBody(BaseModel):
    handle: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class MeUpdateBody(BaseModel):
    bio: str | None = Field(default=None, max_length=280)
