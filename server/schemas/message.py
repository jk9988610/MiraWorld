from __future__ import annotations

from pydantic import BaseModel, Field


class MessagePublic(BaseModel):
    id: int
    from_kind: str
    from_id: str | None
    from_display: str = ""
    body: str
    ref_type: str | None
    ref_id: str | None
    read_at: str | None
    created_at: str


class MessageListResponse(BaseModel):
    messages: list[MessagePublic]


class MessageSummaryResponse(BaseModel):
    unread_count: int


class MessageSendBody(BaseModel):
    to_handle: str = Field(min_length=2, max_length=32)
    body: str = Field(min_length=1, max_length=500)
    ref_type: str | None = Field(default=None, max_length=32)
    ref_id: str | None = Field(default=None, max_length=64)
