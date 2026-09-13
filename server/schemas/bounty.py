from __future__ import annotations

from pydantic import BaseModel, Field


class BountyCreateBody(BaseModel):
    title: str = Field(min_length=2, max_length=64)
    body: str = Field(default="", max_length=500)
    price_credits: int = Field(ge=1, le=9999)
    city: str = Field(default="潮灯市", min_length=1, max_length=64)
    in_person: bool = False


class BountyPublic(BaseModel):
    id: str
    issuer_id: int
    issuer_handle: str = ""
    worker_id: int | None = None
    worker_handle: str = ""
    city: str
    title: str
    body: str
    price_credits: int
    status: str
    in_person: bool = False
    created_at: str
    updated_at: str


class BountyListResponse(BaseModel):
    open: list[BountyPublic]
    issued: list[BountyPublic]
    taken: list[BountyPublic]
