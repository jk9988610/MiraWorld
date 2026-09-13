from __future__ import annotations

from pydantic import BaseModel


class CatalogItem(BaseModel):
    id: str
    display: str
    tags: list[str] = []


class CatalogOffer(BaseModel):
    id: str
    seller: dict
    place: dict
    gives: dict
    price_credits: int
    display: str
    active: bool = True


class CatalogResponse(BaseModel):
    items: list[CatalogItem]
    offers: list[CatalogOffer]
