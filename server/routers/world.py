from __future__ import annotations

from fastapi import APIRouter, Depends

from deps import get_current_player
from schemas.player import PlayerPublic
from schemas.world import VisitBody
from services.world import get_world_payload, record_visit

router = APIRouter(tags=["world"])


@router.get("/world")
def world_view() -> dict:
    return get_world_payload()


@router.post("/records/visit")
def visit(
    body: VisitBody,
    player: PlayerPublic = Depends(get_current_player),
) -> dict:
    return record_visit(player.id, body.city, body.spot_id)
