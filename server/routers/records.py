from __future__ import annotations

from fastapi import APIRouter, Depends

from deps import get_current_player
from schemas.message import MessageListResponse, MessagePublic, MessageSummaryResponse
from schemas.order import OrderBody, OrderListResponse, OrderPublic
from schemas.player import PlayerPublic
from services.messages import list_messages, mark_read, send_player_message, unread_count
from services.orders import (
    accept_order,
    get_order,
    list_orders,
    list_selling_orders,
    mark_order_ready,
    pickup_order,
    place_order,
)
from schemas.message import MessageSendBody

router = APIRouter(tags=["records"])


@router.post("/records/order", response_model=OrderPublic)
def create_order(
    body: OrderBody,
    player: PlayerPublic = Depends(get_current_player),
) -> OrderPublic:
    return place_order(player.id, body.offer_id)


@router.get("/records/orders", response_model=OrderListResponse)
def my_orders(player: PlayerPublic = Depends(get_current_player)) -> OrderListResponse:
    return list_orders(player.id)


@router.get("/records/orders/{order_id}", response_model=OrderPublic)
def order_detail(
    order_id: str,
    player: PlayerPublic = Depends(get_current_player),
) -> OrderPublic:
    return get_order(player.id, order_id)


@router.get("/records/orders/selling", response_model=OrderListResponse)
def selling_orders(player: PlayerPublic = Depends(get_current_player)) -> OrderListResponse:
    return list_selling_orders(player.id)


@router.post("/records/orders/{order_id}/accept", response_model=OrderPublic)
def order_accept(
    order_id: str,
    player: PlayerPublic = Depends(get_current_player),
) -> OrderPublic:
    return accept_order(player.id, order_id)


@router.post("/records/orders/{order_id}/ready", response_model=OrderPublic)
def order_ready(
    order_id: str,
    player: PlayerPublic = Depends(get_current_player),
) -> OrderPublic:
    return mark_order_ready(player.id, order_id)


@router.post("/records/orders/{order_id}/pickup", response_model=OrderPublic)
def order_pickup(
    order_id: str,
    player: PlayerPublic = Depends(get_current_player),
) -> OrderPublic:
    return pickup_order(player.id, order_id)


@router.get("/records/messages/summary", response_model=MessageSummaryResponse)
def messages_summary(
    player: PlayerPublic = Depends(get_current_player),
) -> MessageSummaryResponse:
    return MessageSummaryResponse(unread_count=unread_count(player.id))


@router.get("/records/messages", response_model=MessageListResponse)
def my_messages(player: PlayerPublic = Depends(get_current_player)) -> MessageListResponse:
    return list_messages(player.id)


@router.post("/records/messages/send", response_model=MessagePublic)
def message_send(
    body: MessageSendBody,
    player: PlayerPublic = Depends(get_current_player),
) -> MessagePublic:
    return send_player_message(
        player.id,
        body.to_handle,
        body.body,
        body.ref_type,
        body.ref_id,
    )


@router.post("/records/messages/{message_id}/read", response_model=MessagePublic)
def message_read(
    message_id: int,
    player: PlayerPublic = Depends(get_current_player),
) -> MessagePublic:
    return mark_read(player.id, message_id)
