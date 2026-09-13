from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException

from auth_util import COOKIE_NAME, decode_token
from schemas.player import PlayerPublic
from services.players import get_player_by_id


def get_current_player(
    miraworld_session: str | None = Cookie(default=None),
) -> PlayerPublic:
    if not miraworld_session:
        raise HTTPException(status_code=401, detail="未登录")
    user_id = decode_token(miraworld_session)
    return get_player_by_id(user_id)
