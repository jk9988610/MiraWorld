from __future__ import annotations

from pydantic import BaseModel, Field


class CompanyCreateBody(BaseModel):
    display_name: str = Field(min_length=2, max_length=32)


class CompanyInstitutionPublic(BaseModel):
    id: str
    display_name: str
    kind: str
    wallet_credits: int
    open: bool
    owner_kind: str
    owner_id: str


class CompanyPublic(BaseModel):
    id: str
    display_name: str
    city: str
    owner_player_id: int
    wallet_credits: int
    created_at: str
    institutions: list[CompanyInstitutionPublic] = []


class AssetBreakdown(BaseModel):
    wallet_credits: int
    company_wallet: int
    institution_wallet: int
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


class CompanyTransferBody(BaseModel):
    direction: str = Field(pattern="^(to_company|to_player)$")
    amount: int = Field(gt=0)


class CompanyTransferResponse(BaseModel):
    ok: bool
    direction: str
    amount: int
    wallet_credits: int
    company_wallet: int


class ProductionLineBody(BaseModel):
    recipe_id: str
    enabled: bool = True


class ProductionLinesBody(BaseModel):
    lines: list[ProductionLineBody]


class InstitutionTransferBody(BaseModel):
    source: str = Field(pattern="^(company|player)$")
    amount: int = Field(gt=0)


class InstitutionOfferBody(BaseModel):
    item_id: str
    display: str = Field(default="", max_length=64)
    price_credits: int = Field(gt=0)
    qty: int = Field(default=1, gt=0)


class InstitutionOfferPublic(BaseModel):
    id: str
    item_id: str
    item_display: str
    qty: int
    price_credits: int
    display: str
    active: bool
    stock: int
    created_at: str


class ProductionInstitutionPublic(BaseModel):
    id: str
    display_name: str
    kind: str
    wallet_credits: int
    production_ready: bool


class ProductionStatusResponse(BaseModel):
    has_shop: bool
    has_company: bool
    company_wallet: int
    shop_open: bool
    institution: ProductionInstitutionPublic | None
    hub: dict | None
    inventory: list[dict]
    production_lines: list[dict]
    available_recipes: list[dict]
    offers: list[InstitutionOfferPublic]
