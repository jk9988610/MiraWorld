from __future__ import annotations

from pydantic import BaseModel


class MessagePublic(BaseModel):
    id: int
    from_kind: str
    from_id: str | None = None
    body: str
    ref_type: str | None = None
    ref_id: str | None = None
    read_at: str | None = None
    created_at: str


class MessageListResponse(BaseModel):
    messages: list[MessagePublic]


class MessageSummaryResponse(BaseModel):
    unread_count: int
