from __future__ import annotations

from fastapi import APIRouter, Depends

from deps import get_current_player
from schemas.capital import (
    CapitalStatusResponse,
    CompanyCreateBody,
    CompanyPublic,
    DailyInvestmentResponse,
)
from schemas.player import PlayerPublic
from services.capital.company import create_company
from services.capital.investment import claim_daily_investment, get_capital_status

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
