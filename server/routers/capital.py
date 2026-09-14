from __future__ import annotations

from fastapi import APIRouter, Depends

from deps import get_current_player
from schemas.capital import (
    CapitalStatusResponse,
    CompanyCreateBody,
    CompanyPublic,
    CompanyTransferBody,
    CompanyTransferResponse,
    DailyInvestmentResponse,
    InstitutionOfferBody,
    InstitutionOfferPublic,
    InstitutionTransferBody,
    ProductionLinesBody,
    ProductionStatusResponse,
)
from schemas.player import PlayerPublic
from services.capital.company import create_company, transfer_company_funds
from services.capital.investment import claim_daily_investment, get_capital_status
from services.capital.production import (
    create_institution_offer,
    get_production_status,
    set_institution_offer_active,
    setup_device_plant,
    transfer_to_institution,
    update_production_lines,
)

router = APIRouter(prefix="/capital", tags=["capital"])


@router.get("/status", response_model=CapitalStatusResponse)
def capital_status(player: PlayerPublic = Depends(get_current_player)) -> dict:
    return get_capital_status(player.id)


@router.post("/daily-investment", response_model=DailyInvestmentResponse)
def daily_investment(player: PlayerPublic = Depends(get_current_player)) -> dict:
    return claim_daily_investment(player.id)


@router.post("/company", response_model=CompanyPublic)
def register_company(
    body: CompanyCreateBody,
    player: PlayerPublic = Depends(get_current_player),
) -> dict:
    return create_company(player.id, body.display_name)


@router.post("/company/transfer", response_model=CompanyTransferResponse)
def company_transfer(
    body: CompanyTransferBody,
    player: PlayerPublic = Depends(get_current_player),
) -> dict:
    return transfer_company_funds(player.id, body.direction, body.amount)


@router.get("/production", response_model=ProductionStatusResponse)
def production_status(player: PlayerPublic = Depends(get_current_player)) -> dict:
    return get_production_status(player.id)


@router.post("/production/setup", response_model=ProductionStatusResponse)
def production_setup(player: PlayerPublic = Depends(get_current_player)) -> dict:
    return setup_device_plant(player.id)


@router.patch("/production/lines", response_model=ProductionStatusResponse)
def production_lines(
    body: ProductionLinesBody,
    player: PlayerPublic = Depends(get_current_player),
) -> dict:
    return update_production_lines(
        player.id,
        [line.model_dump() for line in body.lines],
    )


@router.post("/production/institution-transfer")
def production_institution_transfer(
    body: InstitutionTransferBody,
    player: PlayerPublic = Depends(get_current_player),
) -> dict:
    return transfer_to_institution(player.id, body.source, body.amount)


@router.post("/production/offers", response_model=InstitutionOfferPublic)
def production_create_offer(
    body: InstitutionOfferBody,
    player: PlayerPublic = Depends(get_current_player),
) -> dict:
    return create_institution_offer(
        player.id,
        body.item_id,
        body.display,
        body.price_credits,
        body.qty,
    )


@router.patch("/production/offers/{offer_id}", response_model=InstitutionOfferPublic)
def production_toggle_offer(
    offer_id: str,
    active: bool,
    player: PlayerPublic = Depends(get_current_player),
) -> dict:
    return set_institution_offer_active(player.id, offer_id, active)
