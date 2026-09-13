from __future__ import annotations

from fastapi import APIRouter, Depends

from db import db
from deps import get_current_player
from schemas.economy import SpotlightResponse
from schemas.player import PlayerPublic
from schemas.shop import (
    MarketResponse,
    PlayerOfferBody,
    PlayerOfferPublic,
    ShopApplyBody,
    ShopMeResponse,
    ShopPublic,
)
from services.economy.spotlight import list_spotlight
from services.shops import (
    apply_shop,
    create_player_offer,
    get_my_shop_payload,
    list_market,
    set_offer_active,
    set_shop_auto,
    set_shop_open,
)

router = APIRouter(prefix="/shop", tags=["shop"])

_SHOP_SPOTLIGHT_MAP = {
    "inst_chen_noodle": "inst_chen_noodle",
    "inst_chaodeng_clinic": "inst_chaodeng_clinic",
    "inst_east_smithy": "inst_east_smithy",
    "npc_chen": "inst_chen_noodle",
}


def _resolve_institution_id(shop_id: str) -> str | None:
    if shop_id in _SHOP_SPOTLIGHT_MAP:
        return _SHOP_SPOTLIGHT_MAP[shop_id]
    return shop_id if shop_id.startswith("inst_") else None


@router.get("/me", response_model=ShopMeResponse)
def shop_me(player: PlayerPublic = Depends(get_current_player)) -> ShopMeResponse:
    return get_my_shop_payload(player.id)


@router.post("/apply", response_model=ShopPublic)
def shop_apply(
    body: ShopApplyBody,
    player: PlayerPublic = Depends(get_current_player),
) -> ShopPublic:
    return apply_shop(player.id, body.display_name)


@router.patch("/open", response_model=ShopPublic)
def shop_toggle_open(
    is_open: bool,
    player: PlayerPublic = Depends(get_current_player),
) -> ShopPublic:
    return set_shop_open(player.id, is_open)


@router.post("/offers", response_model=PlayerOfferPublic)
def shop_create_offer(
    body: PlayerOfferBody,
    player: PlayerPublic = Depends(get_current_player),
) -> PlayerOfferPublic:
    return create_player_offer(
        player.id,
        body.item_id,
        body.display,
        body.price_credits,
        body.qty,
    )


@router.patch("/offers/{offer_id}", response_model=PlayerOfferPublic)
def shop_toggle_offer(
    offer_id: str,
    active: bool,
    player: PlayerPublic = Depends(get_current_player),
) -> PlayerOfferPublic:
    return set_offer_active(player.id, offer_id, active)


@router.patch("/auto", response_model=ShopPublic)
def shop_toggle_auto(
    auto_on: bool,
    player: PlayerPublic = Depends(get_current_player),
) -> ShopPublic:
    return set_shop_auto(player.id, auto_on)


@router.get("/market", response_model=MarketResponse)
def shop_market(city: str = "潮灯市") -> MarketResponse:
    return list_market(city)


@router.get("/{shop_id}/spotlight", response_model=SpotlightResponse)
def shop_spotlight(shop_id: str) -> SpotlightResponse:
    institution_id = _resolve_institution_id(shop_id)
    if institution_id is None:
        return SpotlightResponse(institution_id=shop_id, items=[])
    with db() as conn:
        inst = conn.execute(
            "SELECT id FROM institutions WHERE id = ?",
            (institution_id,),
        ).fetchone()
        if inst is None:
            return SpotlightResponse(institution_id=shop_id, items=[])
        items = list_spotlight(conn, institution_id)
    return SpotlightResponse(institution_id=institution_id, items=items)
