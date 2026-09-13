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
