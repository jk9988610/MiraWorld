from __future__ import annotations

from fastapi import APIRouter, Depends

from deps import get_current_player
from schemas.bounty import BountyCreateBody, BountyListResponse, BountyPublic
from schemas.player import PlayerPublic
from services.bounties import (
    cancel_bounty,
    create_bounty,
    list_bounties,
    settle_bounty,
    submit_bounty,
    take_bounty,
)

router = APIRouter(prefix="/bounties", tags=["bounties"])


@router.post("", response_model=BountyPublic)
def bounty_create(
    body: BountyCreateBody,
    player: PlayerPublic = Depends(get_current_player),
) -> BountyPublic:
    return create_bounty(
        player.id,
        body.kind,
        body.item_id,
        body.qty,
        body.price_credits,
        body.city,
    )


@router.get("", response_model=BountyListResponse)
def bounty_list(
    city: str = "潮灯市",
    player: PlayerPublic = Depends(get_current_player),
) -> BountyListResponse:
    return list_bounties(player.id, city)


@router.post("/{bounty_id}/take", response_model=BountyPublic)
def bounty_take(
    bounty_id: str,
    player: PlayerPublic = Depends(get_current_player),
) -> BountyPublic:
    return take_bounty(player.id, bounty_id)


@router.post("/{bounty_id}/submit", response_model=BountyPublic)
def bounty_submit(
    bounty_id: str,
    player: PlayerPublic = Depends(get_current_player),
) -> BountyPublic:
    return submit_bounty(player.id, bounty_id)


@router.post("/{bounty_id}/settle", response_model=BountyPublic)
def bounty_settle(
    bounty_id: str,
    player: PlayerPublic = Depends(get_current_player),
) -> BountyPublic:
    return settle_bounty(player.id, bounty_id)


@router.post("/{bounty_id}/cancel", response_model=BountyPublic)
def bounty_cancel(
    bounty_id: str,
    player: PlayerPublic = Depends(get_current_player),
) -> BountyPublic:
    return cancel_bounty(player.id, bounty_id)
