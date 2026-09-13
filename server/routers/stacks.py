from __future__ import annotations

from fastapi import APIRouter, Depends

from deps import get_current_player
from schemas.player import PlayerPublic
from schemas.stack import StackListResponse
from services.inventory import list_stacks

router = APIRouter(tags=["stacks"])


@router.get("/stacks", response_model=StackListResponse)
def my_stacks(player: PlayerPublic = Depends(get_current_player)) -> StackListResponse:
    return list_stacks(player.id)
