from __future__ import annotations

from fastapi import APIRouter, Depends

from deps import get_current_player
from schemas.player import PlayerPublic
from schemas.world_gate import (
    FocusOverrideBody,
    FocusResponse,
    PlayerScheduleBody,
    PlayerScheduleResponse,
    SoloTickResponse,
    SoloWorldStatusResponse,
    WorldClockResponse,
    WorldContinueBody,
    WorldGateResponse,
    WorldLoadBody,
    WorldNewBody,
    WorldSessionResponse,
    WorldSpeedBody,
)
from services.world_session.gate import (
    autosave,
    continue_save,
    create_new_save,
    exit_session,
    get_clock,
    get_gate_status,
    get_session,
    load_save,
    manual_save,
    set_speed,
)
from services.world_session.schedule import get_focus, get_schedule, set_focus_override, update_schedule
from services.world_session.solo_world import advance_solo_tick, get_solo_status

router = APIRouter(tags=["world-gate"])


@router.get("/world/gate", response_model=WorldGateResponse)
def world_gate(player: PlayerPublic = Depends(get_current_player)) -> dict:
    return get_gate_status(player.id, player.handle)


@router.get("/world/session", response_model=WorldSessionResponse)
def world_session(player: PlayerPublic = Depends(get_current_player)) -> dict:
    return get_session(player.id)


@router.post("/world/new", response_model=WorldSessionResponse)
def world_new(body: WorldNewBody, player: PlayerPublic = Depends(get_current_player)) -> dict:
    save = create_new_save(
        player.id,
        player.handle,
        body.scope,
        body.display_name,
        body.ironman,
    )
    return {"active": True, "save": save}


@router.post("/world/continue", response_model=WorldSessionResponse)
def world_continue(
    body: WorldContinueBody,
    player: PlayerPublic = Depends(get_current_player),
) -> dict:
    save = continue_save(player.id, body.scope)
    return {"active": True, "save": save}


@router.post("/world/load", response_model=WorldSessionResponse)
def world_load(body: WorldLoadBody, player: PlayerPublic = Depends(get_current_player)) -> dict:
    save = load_save(player.id, body.scope, body.save_id)
    return {"active": True, "save": save}


@router.post("/world/autosave")
def world_autosave(player: PlayerPublic = Depends(get_current_player)) -> dict:
    return autosave(player.id)


@router.post("/world/exit")
def world_exit(player: PlayerPublic = Depends(get_current_player)) -> dict:
    return exit_session(player.id)


@router.post("/world/save")
def world_manual_save(player: PlayerPublic = Depends(get_current_player)) -> dict:
    return manual_save(player.id)


@router.get("/world/clock", response_model=WorldClockResponse)
def world_clock(player: PlayerPublic = Depends(get_current_player)) -> dict:
    return get_clock(player.id)


@router.patch("/world/speed", response_model=WorldClockResponse)
def world_speed(body: WorldSpeedBody, player: PlayerPublic = Depends(get_current_player)) -> dict:
    set_speed(player.id, body.speed)
    return get_clock(player.id)


@router.get("/world/solo/status", response_model=SoloWorldStatusResponse)
def world_solo_status(player: PlayerPublic = Depends(get_current_player)) -> dict:
    return get_solo_status(player.id)


@router.post("/world/tick", response_model=SoloTickResponse)
def world_solo_tick(player: PlayerPublic = Depends(get_current_player)) -> dict:
    return advance_solo_tick(player.id)


@router.get("/me/schedule", response_model=PlayerScheduleResponse)
def me_schedule(player: PlayerPublic = Depends(get_current_player)) -> dict:
    data = get_schedule(player.id)
    return {
        "timezone": data["timezone"],
        "work_windows": data["work_windows"],
        "holidays": data["holidays"],
        "notify_sound": data["notify_sound"],
    }


@router.patch("/me/schedule", response_model=PlayerScheduleResponse)
def me_schedule_update(
    body: PlayerScheduleBody,
    player: PlayerPublic = Depends(get_current_player),
) -> dict:
    data = update_schedule(
        player.id,
        {
            "timezone": body.timezone,
            "work_windows": [w.model_dump() for w in body.work_windows],
            "holidays": body.holidays,
            "notify_sound": body.notify_sound,
        },
    )
    return {
        "timezone": data["timezone"],
        "work_windows": data["work_windows"],
        "holidays": data["holidays"],
        "notify_sound": data["notify_sound"],
    }


@router.get("/me/focus", response_model=FocusResponse)
def me_focus(player: PlayerPublic = Depends(get_current_player)) -> dict:
    return get_focus(player.id)


@router.post("/me/focus/override", response_model=FocusResponse)
def me_focus_override(
    body: FocusOverrideBody,
    player: PlayerPublic = Depends(get_current_player),
) -> dict:
    return set_focus_override(player.id, body.focus)
