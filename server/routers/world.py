from __future__ import annotations

from fastapi import APIRouter, Depends

from deps import get_current_player
from schemas.player import PlayerPublic
from schemas.world import SpotLootBody, VisitBody
from services.inventory import list_stacks
from services.spot_loot import claim_spot_loot
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


@router.post("/records/spot/put")
def spot_put_to_stack(
    body: SpotLootBody,
    player: PlayerPublic = Depends(get_current_player),
) -> dict:
    result = claim_spot_loot(player.id, body.city, body.spot_id, "put")
    return {**result, "stacks": list_stacks(player.id).model_dump()["stacks"]}


@router.post("/records/spot/consume")
def spot_consume_item(
    body: SpotLootBody,
    player: PlayerPublic = Depends(get_current_player),
) -> dict:
    return claim_spot_loot(player.id, body.city, body.spot_id, "consume")


@router.post("/records/spot/use")
def spot_use_item(
    body: SpotLootBody,
    player: PlayerPublic = Depends(get_current_player),
) -> dict:
    return claim_spot_loot(player.id, body.city, body.spot_id, "use")
