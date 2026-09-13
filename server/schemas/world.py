from __future__ import annotations

from pydantic import BaseModel, Field


class VisitBody(BaseModel):
    city: str = Field(min_length=1, max_length=64)
    spot_id: str | None = Field(default=None, max_length=64)


class SpotLootBody(BaseModel):
    city: str = Field(min_length=1, max_length=64)
    spot_id: str = Field(min_length=1, max_length=64)
