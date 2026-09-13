from __future__ import annotations

from fastapi import HTTPException

from config_loader import items


def get_item(item_id: str) -> dict:
    for item in items().get("items", []):
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="找不到这个物品")


def item_tags(item_id: str) -> list[str]:
    return list(get_item(item_id).get("tags", []))


def can_consume(tags: list[str]) -> bool:
    return "food" in tags and "consumable" in tags


def can_use(tags: list[str]) -> bool:
    return "tool" in tags


def allowed_stack_actions(tags: list[str]) -> list[str]:
    actions: list[str] = []
    if can_consume(tags):
        actions.append("consume")
    if can_use(tags):
        actions.append("use")
    return actions
