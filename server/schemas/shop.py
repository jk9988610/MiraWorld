from __future__ import annotations

from pydantic import BaseModel, Field


class ShopApplyBody(BaseModel):
    display_name: str = Field(min_length=2, max_length=32)


class ShopPublic(BaseModel):
    player_id: int
    handle: str
    display_name: str
    city: str
    open: bool
    created_at: str


class PlayerOfferBody(BaseModel):
    item_id: str = Field(min_length=1, max_length=64)
    display: str = Field(min_length=1, max_length=64)
    price_credits: int = Field(ge=1, le=9999)
    qty: int = Field(default=1, ge=1, le=99)


class PlayerOfferPublic(BaseModel):
    id: str
    player_id: int
    item_id: str
    qty: int
    price_credits: int
    display: str
    active: bool
    created_at: str


class ShopMeResponse(BaseModel):
    shop: ShopPublic | None
    registration_fee: int
    offers: list[PlayerOfferPublic]


class MarketShopPublic(BaseModel):
    player_id: int
    handle: str
    display_name: str
    city: str
    offers: list[PlayerOfferPublic]


class MarketResponse(BaseModel):
    shops: list[MarketShopPublic]
