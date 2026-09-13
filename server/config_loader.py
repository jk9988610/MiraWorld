"""Load static JSON config from server/config/."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent / "config"


@lru_cache(maxsize=16)
def load_json(name: str) -> dict:
    path = CONFIG_DIR / name
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def welcome() -> dict:
    return load_json("welcome.json")


def world() -> dict:
    return load_json("locations.json")


def schema() -> dict:
    return load_json("schema.json")


def items() -> dict:
    return load_json("items.json")


def offers() -> dict:
    return load_json("offers.json")


def game_messages() -> dict:
    return load_json("messages.json")


def utopia_economy() -> dict:
    return load_json("economy/utopia.json")


def economy_institutions() -> dict:
    return load_json("economy/institutions.json")


def economy_pop_groups() -> dict:
    return load_json("economy/pop_groups.json")


def pop_spotlight_names() -> dict:
    return load_json("names/pop_spotlight.json")


def capitalist_economy() -> dict:
    return load_json("economy/capitalist.json")
