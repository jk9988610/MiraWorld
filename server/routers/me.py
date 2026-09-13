from __future__ import annotations

from fastapi import APIRouter, Depends

from deps import get_current_player
from schemas.player import MeUpdateBody, PlayerPublic
from services.players import update_bio
from services.world import list_visits

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=PlayerPublic)
def get_me(player: PlayerPublic = Depends(get_current_player)) -> PlayerPublic:
    return player


@router.patch("", response_model=PlayerPublic)
def patch_me(
    body: MeUpdateBody,
    player: PlayerPublic = Depends(get_current_player),
) -> PlayerPublic:
    if body.bio is not None:
        return update_bio(player.id, body.bio)
    return player


@router.get("/visits")
def my_visits(player: PlayerPublic = Depends(get_current_player)) -> dict:
    return {"visits": list_visits(player.id)}
