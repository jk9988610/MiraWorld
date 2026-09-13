#!/usr/bin/env python3
"""Run MVP demo flow N times against MiraWorld API (see 游戏想法/33 §三)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

DEFAULT_BASE = "http://8.133.252.224/miraworld/api"
CITY = "潮灯市"
SPOT = "spot_sunset"
OFFER = "offer_standard_noodle"
PASSWORD = "SmokeDemo1!"


class DemoError(RuntimeError):
    pass


def api(base: str, opener, method: str, path: str, body: dict | None = None) -> dict:
    url = f"{base.rstrip('/')}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise DemoError(f"{method} {path} -> {exc.code}: {detail}") from exc


def run_once(base: str, run_index: int) -> None:
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    handle = f"烟{run_index:02d}{uuid.uuid4().hex[:4]}"

    health = api(base, opener, "GET", "/health")
    if not health.get("ok"):
        raise DemoError(f"health check failed: {health}")

    player = api(
        base,
        opener,
        "POST",
        "/auth/register",
        {"handle": handle, "password": PASSWORD},
    )
    if player.get("wallet_credits") != 300:
        raise DemoError(f"expected wallet 300, got {player.get('wallet_credits')}")
    if player.get("city") != CITY:
        raise DemoError(f"expected city {CITY}, got {player.get('city')}")

    api(base, opener, "POST", "/records/visit", {"city": CITY})
    visit = api(
        base,
        opener,
        "POST",
        "/records/visit",
        {"city": CITY, "spot_id": SPOT},
    )
    if not visit.get("message"):
        raise DemoError("spot visit missing message")

    order = api(base, opener, "POST", "/records/order", {"offer_id": OFFER})
    if order.get("status") != "ready":
        raise DemoError(f"order not ready: {order.get('status')}")
    order_id = order["id"]

    picked = api(base, opener, "POST", f"/records/orders/{order_id}/pickup", None)
    if picked.get("status") != "settled":
        raise DemoError(f"pickup not settled: {picked.get('status')}")

    me = api(base, opener, "GET", "/me")
    if me.get("wallet_credits") != 285:
        raise DemoError(f"expected wallet 285 after order, got {me.get('wallet_credits')}")

    stacks = api(base, opener, "GET", "/stacks")
    items = stacks.get("stacks") or []
    noodle = next((s for s in items if s.get("item_id") == "item_noodle_bowl"), None)
    if not noodle or int(noodle.get("qty", 0)) < 1:
        raise DemoError(f"stack missing noodle bowl: {items}")

    msgs = api(base, opener, "GET", "/records/messages")
    message_list = msgs.get("messages") or []
    if len(message_list) < 2:
        raise DemoError(f"expected >=2 messages, got {len(message_list)}")

    summary = api(base, opener, "GET", "/records/messages/summary")
    if "unread_count" not in summary:
        raise DemoError(f"messages summary missing unread_count: {summary}")

    consumed = api(base, opener, "POST", "/stacks/item_noodle_bowl/consume", None)
    if consumed.get("qty", 1) != 0:
        raise DemoError(f"consume expected qty 0, got {consumed}")

    print(f"  run {run_index}: OK handle={handle}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="MiraWorld MVP smoke demo (HTTP)")
    parser.add_argument(
        "-n",
        "--runs",
        type=int,
        default=5,
        help="Number of full demo passes (default: 5)",
    )
    parser.add_argument(
        "--base",
        default=os.environ.get("MIRAWORLD_API_BASE", DEFAULT_BASE),
        help=f"API base URL (default: {DEFAULT_BASE})",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=0.2,
        help="Seconds between runs",
    )
    args = parser.parse_args()
    if args.runs < 1:
        print("--runs must be >= 1", file=sys.stderr)
        return 1

    base = args.base.rstrip("/")
    print(f"Smoke demo: {args.runs} run(s) -> {base}", flush=True)
    for i in range(1, args.runs + 1):
        run_once(base, i)
        if i < args.runs and args.pause > 0:
            time.sleep(args.pause)
    print(f"All {args.runs} run(s) passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
