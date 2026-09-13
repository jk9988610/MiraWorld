from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


BountyKind = Literal["buy", "sell"]
MAX_LISTED_BOUNTIES = 10


class BountyCreateBody(BaseModel):
    kind: BountyKind
    item_id: str = Field(min_length=1, max_length=64)
    qty: int = Field(ge=1, le=9999)
    price_credits: int = Field(ge=1, le=9999)
    city: str = Field(default="潮灯市", min_length=1, max_length=64)


class BountyPublic(BaseModel):
    id: str
    issuer_id: int
    issuer_handle: str = ""
    worker_id: int | None = None
    worker_handle: str = ""
    city: str
    kind: str
    item_id: str
    item_display: str
    qty: int
    title: str
    price_credits: int
    status: str
    created_at: str
    updated_at: str


class BountyListResponse(BaseModel):
    open: list[BountyPublic]
    issued: list[BountyPublic]
    taken: list[BountyPublic]
