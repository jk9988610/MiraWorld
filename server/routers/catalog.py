from __future__ import annotations

from fastapi import APIRouter

from schemas.catalog import CatalogResponse
from services.catalog import get_catalog

router = APIRouter(tags=["catalog"])


@router.get("/catalog", response_model=CatalogResponse)
def catalog_view() -> CatalogResponse:
    return get_catalog()
