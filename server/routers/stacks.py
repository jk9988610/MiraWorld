from __future__ import annotations

from fastapi import APIRouter, Depends

from deps import get_current_player
from schemas.player import PlayerPublic
from schemas.stack import StackActionResponse, StackListResponse
from services.inventory import consume_stack_item, list_stacks, use_stack_item

router = APIRouter(tags=["stacks"])


def _action_response(player_id: int, result: dict) -> StackActionResponse:
    stacks = list_stacks(player_id).stacks
    return StackActionResponse(
        item_id=result["item_id"],
        display=result["display"],
        qty=result["qty"],
        message=result["message"],
        stacks=stacks,
    )


@router.get("/stacks", response_model=StackListResponse)
def my_stacks(player: PlayerPublic = Depends(get_current_player)) -> StackListResponse:
    return list_stacks(player.id)


@router.post("/stacks/{item_id}/consume", response_model=StackActionResponse)
def stack_consume(
    item_id: str,
    player: PlayerPublic = Depends(get_current_player),
) -> StackActionResponse:
    result = consume_stack_item(player.id, item_id)
    return _action_response(player.id, result)


@router.post("/stacks/{item_id}/use", response_model=StackActionResponse)
def stack_use(
    item_id: str,
    player: PlayerPublic = Depends(get_current_player),
) -> StackActionResponse:
    result = use_stack_item(player.id, item_id)
    return _action_response(player.id, result)
