from __future__ import annotations

from fastapi import APIRouter, Depends

from deps import get_current_player
from schemas.player import PlayerPublic
from schemas.shop import (
    MarketResponse,
    PlayerOfferBody,
    PlayerOfferPublic,
    ShopApplyBody,
    ShopMeResponse,
    ShopPublic,
)
from services.shops import (
    apply_shop,
    create_player_offer,
    get_my_shop_payload,
    list_market,
    set_offer_active,
    set_shop_open,
)

router = APIRouter(prefix="/shop", tags=["shop"])


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


@router.get("/market", response_model=MarketResponse)
def shop_market(city: str = "潮灯市") -> MarketResponse:
    return list_market(city)
