from __future__ import annotations

from pydantic import BaseModel, Field


class CompanyCreateBody(BaseModel):
    display_name: str = Field(min_length=2, max_length=32)


class CompanyPublic(BaseModel):
    id: str
    display_name: str
    city: str
    owner_player_id: int
    created_at: str


class AssetBreakdown(BaseModel):
    wallet_credits: int
    shop_value: int
    inventory_value: int
    total: int


class DailyGrantPublic(BaseModel):
    grant_date: str
    amount: int
    asset_total: int
    asset_pct: float
    created_at: str


class CapitalStatusResponse(BaseModel):
    assets: AssetBreakdown
    company: CompanyPublic | None
    has_shop: bool
    last_grant: DailyGrantPublic | None
    can_claim_today: bool
    config: dict


class DailyInvestmentResponse(BaseModel):
    ok: bool
    grant: DailyGrantPublic
    wallet_credits: int
