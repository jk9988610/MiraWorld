from __future__ import annotations

from pydantic import BaseModel, Field


class WorldSavePublic(BaseModel):
    id: str
    scope: str
    display_name: str
    ironman: bool
    world_day: int
    speed: str
    last_played_at: str
    created_at: str


class WorldGateResponse(BaseModel):
    can_continue_solo: bool
    can_load_solo: bool
    can_new_solo: bool
    can_continue_multi: bool
    can_load_multi: bool
    can_new_multi: bool
    last_solo_save_id: str | None
    last_multi_save_id: str | None
    solo_saves: list[WorldSavePublic]
    multi_saves: list[WorldSavePublic]
    active_session: WorldSavePublic | None


class WorldNewBody(BaseModel):
    scope: str = Field(pattern="^(solo|multi)$")
    display_name: str = Field(default="", max_length=32)
    ironman: bool = False


class WorldLoadBody(BaseModel):
    scope: str = Field(pattern="^(solo|multi)$")
    save_id: str


class WorldContinueBody(BaseModel):
    scope: str = Field(pattern="^(solo|multi)$")


class WorldSessionResponse(BaseModel):
    active: bool
    save: WorldSavePublic | None


class WorldClockResponse(BaseModel):
    scope: str | None
    world_day: int
    speed_label: str
    next_tick_hint: str | None = None


class WorldSpeedBody(BaseModel):
    speed: str = Field(pattern="^(pause|slow|mid|fast|fastest)$")


class ScheduleWindow(BaseModel):
    dow: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    start: str = "09:00"
    end: str = "18:00"


class PlayerScheduleBody(BaseModel):
    timezone: str = "Asia/Shanghai"
    work_windows: list[ScheduleWindow] = Field(default_factory=list)
    holidays: list[str] = Field(default_factory=list)
    notify_sound: bool = True


class PlayerScheduleResponse(BaseModel):
    timezone: str
    work_windows: list[ScheduleWindow]
    holidays: list[str]
    notify_sound: bool


class FocusResponse(BaseModel):
    focus: str
    source: str
    in_work_window: bool
    override_until: str | None = None


class FocusOverrideBody(BaseModel):
    focus: str = Field(pattern="^(company|personal)$")
