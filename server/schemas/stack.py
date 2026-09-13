from __future__ import annotations

from pydantic import BaseModel


class StackEntry(BaseModel):
    item_id: str
    display: str
    qty: int
    tags: list[str] = []


class StackListResponse(BaseModel):
    stacks: list[StackEntry]
