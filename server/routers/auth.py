from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from auth_util import (
    clear_session_cookie,
    hash_password,
    issue_session_cookie,
    verify_password,
)
from deps import get_current_player
from schemas.player import LoginBody, PlayerPublic, RegisterBody
from services.players import login_player, register_player
from services.world_session.gate import autosave

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=PlayerPublic)
def register(body: RegisterBody, response: Response) -> PlayerPublic:
    player = register_player(
        body.handle,
        body.password,
        hash_password,
        body.email,
    )
    issue_session_cookie(response, player.id, player.handle, body.remember)
    return player


@router.post("/login", response_model=PlayerPublic)
def login(body: LoginBody, response: Response) -> PlayerPublic:
    player = login_player(body.handle, body.password, verify_password)
    issue_session_cookie(response, player.id, player.handle, body.remember)
    return player


@router.post("/logout")
def logout(
    response: Response,
    player: PlayerPublic = Depends(get_current_player),
) -> dict[str, bool]:
    autosave(player.id)
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=PlayerPublic)
def me(player: PlayerPublic = Depends(get_current_player)) -> PlayerPublic:
    return player
