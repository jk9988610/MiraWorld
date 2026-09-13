from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException

from db import db
from schemas.economy import EconomyStatusResponse, EconomyTickResponse, SpotlightResponse
from services.economy.spotlight import list_spotlight
from services.economy.tick import get_economy_status, run_daily_tick

router = APIRouter(prefix="/economy", tags=["economy"])

TICK_SECRET = os.environ.get("MIRAWORLD_TICK_SECRET", "dev-tick-secret")


def _verify_tick_secret(secret: str | None) -> None:
    if not secret or secret != TICK_SECRET:
        raise HTTPException(status_code=403, detail="tick secret invalid")


@router.get("/status", response_model=EconomyStatusResponse)
def economy_status(city: str = "潮灯市") -> dict:
    return get_economy_status(city)


@router.post("/tick", response_model=EconomyTickResponse)
def economy_tick(
    city: str = "潮灯市",
    force: bool = False,
    x_tick_secret: str | None = Header(default=None, alias="X-Tick-Secret"),
) -> dict:
    _verify_tick_secret(x_tick_secret)
    return run_daily_tick(city, force=force)


@router.get("/institutions/{institution_id}/spotlight", response_model=SpotlightResponse)
def institution_spotlight(institution_id: str) -> SpotlightResponse:
    with db() as conn:
        inst = conn.execute(
            "SELECT id FROM institutions WHERE id = ?",
            (institution_id,),
        ).fetchone()
        if inst is None:
            raise HTTPException(status_code=404, detail="机构不存在")
        items = list_spotlight(conn, institution_id)
    return SpotlightResponse(
        institution_id=institution_id,
        items=items,
    )
