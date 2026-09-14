from __future__ import annotations

from pydantic import BaseModel


class EconomyInstitutionPublic(BaseModel):
    id: str
    display_name: str
    kind: str
    wallet_credits: int
    open: bool
    offer_id: str | None = None


class EconomyPopGroupPublic(BaseModel):
    id: str
    headcount: int
    wallet_credits: int
    primary_institution_id: str | None = None
    job_type: str | None = None
    job_display: str | None = None
    satisfaction: int = 0


class HubResourcePublic(BaseModel):
    resource_id: str
    display: str
    qty: int
    price_credits: int
    guide_price: int


class HubStatusPublic(BaseModel):
    city: str
    resources: list[HubResourcePublic]


class EconomyStatusResponse(BaseModel):
    city: str
    hub: HubStatusPublic | None = None
    institutions: list[EconomyInstitutionPublic]
    pop_groups: dict
    welfare_fund: dict | None
    last_tick: dict | None
    dashboard: dict
    config: dict


class EconomyAuditResponse(BaseModel):
    ok: bool
    city: str
    checks: dict


class EconomyTickResponse(BaseModel):
    ok: bool
    city: str
    tick_date: str | None = None
    reason: str | None = None
    summary: dict | None = None


class SpotlightItem(BaseModel):
    display_name: str
    job_display: str
    pop_group_id: str
    order_id: str
    created_at: str


class SpotlightResponse(BaseModel):
    institution_id: str
    items: list[SpotlightItem]
