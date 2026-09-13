from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from auth_util import (
    clear_session_cookie,
    create_token,
    hash_password,
    set_session_cookie,
    verify_password,
)
from deps import get_current_player
from schemas.player import LoginBody, PlayerPublic, RegisterBody
from services.players import login_player, register_player

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=PlayerPublic)
def register(body: RegisterBody, response: Response) -> PlayerPublic:
    player = register_player(
        body.handle,
        body.password,
        hash_password,
        body.email,
    )
    set_session_cookie(response, create_token(player.id, player.handle))
    return player


@router.post("/login", response_model=PlayerPublic)
def login(body: LoginBody, response: Response) -> PlayerPublic:
    player = login_player(body.handle, body.password, verify_password)
    set_session_cookie(response, create_token(player.id, player.handle))
    return player


@router.post("/logout")
def logout(response: Response) -> dict[str, bool]:
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=PlayerPublic)
def me(player: PlayerPublic = Depends(get_current_player)) -> PlayerPublic:
    return player
