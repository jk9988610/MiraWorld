from __future__ import annotations

from pydantic import BaseModel, Field


class OrderBody(BaseModel):
    offer_id: str = Field(min_length=1, max_length=64)
    in_person: bool = False


class OrderPublic(BaseModel):
    id: str
    buyer_id: int
    seller_kind: str
    seller_id: str
    city: str
    offer_id: str
    status: str
    price_credits: int
    escrow_credits: int
    display: str = ""
    item_id: str = ""
    item_qty: int = 0
    created_at: str
    updated_at: str


class OrderListResponse(BaseModel):
    orders: list[OrderPublic]
