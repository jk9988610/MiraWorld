from __future__ import annotations

from fastapi import HTTPException

from config_loader import items, offers
from schemas.catalog import CatalogItem, CatalogOffer, CatalogResponse


def _active_npc_offers() -> list[dict]:
    return [o for o in offers().get("offers", []) if o.get("active", True)]


def _active_offers() -> list[dict]:
    from services.shops import active_player_offers_catalog

    return _active_npc_offers() + active_player_offers_catalog()


def get_offer(offer_id: str) -> dict:
    for offer in _active_offers():
        if offer["id"] == offer_id:
            return offer
    raise HTTPException(status_code=404, detail="找不到这个商品")


def get_catalog() -> CatalogResponse:
    item_list = [
        CatalogItem(**item) for item in items().get("items", [])
    ]
    offer_list = [CatalogOffer(**offer) for offer in _active_offers()]
    return CatalogResponse(items=item_list, offers=offer_list)


def item_display(item_id: str) -> str:
    for item in items().get("items", []):
        if item["id"] == item_id:
            return item.get("display", item_id)
    return item_id
