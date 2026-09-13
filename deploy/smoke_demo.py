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
    order_msgs = [m for m in message_list if m.get("ref_type") == "order"]
    if order_msgs:
        raise DemoError(f"当面点面不应有订单通知，got {len(order_msgs)}")

    summary = api(base, opener, "GET", "/records/messages/summary")
    if "unread_count" not in summary:
        raise DemoError(f"messages summary missing unread_count: {summary}")

    consumed = api(base, opener, "POST", "/stacks/item_noodle_bowl/consume", None)
    if consumed.get("qty", 1) != 0:
        raise DemoError(f"consume expected qty 0, got {consumed}")

    print(f"  run {run_index}: OK handle={handle}", flush=True)


    print(f"  run {run_index}: OK handle={handle}", flush=True)


def run_v12_once(base: str, run_index: int) -> None:
    suffix = uuid.uuid4().hex[:6]
    seller_handle = f"店{suffix[:4]}"
    buyer_handle = f"客{suffix[2:]}"

    seller_jar = CookieJar()
    seller_opener = build_opener(HTTPCookieProcessor(seller_jar))
    buyer_jar = CookieJar()
    buyer_opener = build_opener(HTTPCookieProcessor(buyer_jar))

    api(
        base,
        seller_opener,
        "POST",
        "/auth/register",
        {"handle": seller_handle, "password": PASSWORD},
    )
    api(
        base,
        buyer_opener,
        "POST",
        "/auth/register",
        {"handle": buyer_handle, "password": PASSWORD},
    )

    shop = api(
        base,
        seller_opener,
        "POST",
        "/shop/apply",
        {"display_name": f"烟{run_index}号食堂"},
    )
    if not shop.get("display_name"):
        raise DemoError(f"shop apply failed: {shop}")

    offer = api(
        base,
        seller_opener,
        "POST",
        "/shop/offers",
        {
            "item_id": "item_noodle_bowl",
            "display": "试营业汤面",
            "price_credits": 12,
        },
    )
    offer_id = offer.get("id")
    if not offer_id:
        raise DemoError(f"create offer failed: {offer}")

    order = api(base, buyer_opener, "POST", "/records/order", {"offer_id": offer_id, "in_person": True})
    if order.get("status") != "escrowed":
        raise DemoError(f"player order should be escrowed, got {order.get('status')}")
    order_id = order["id"]

    buyer_msgs = api(base, buyer_opener, "GET", "/records/messages")
    buyer_order_msgs = [
        m for m in (buyer_msgs.get("messages") or []) if m.get("ref_type") == "order"
    ]
    if buyer_order_msgs:
        raise DemoError(f"当面点单买家不应收到订单通知: {buyer_order_msgs}")

    accepted = api(base, seller_opener, "POST", f"/records/orders/{order_id}/accept", None)
    if accepted.get("status") != "processing":
        raise DemoError(f"accept expected processing, got {accepted.get('status')}")

    ready = api(base, seller_opener, "POST", f"/records/orders/{order_id}/ready", None)
    if ready.get("status") != "ready":
        raise DemoError(f"ready expected ready, got {ready.get('status')}")

    settled = api(base, buyer_opener, "POST", f"/records/orders/{order_id}/pickup", None)
    if settled.get("status") != "settled":
        raise DemoError(f"pickup expected settled, got {settled.get('status')}")

    seller_me = api(base, seller_opener, "GET", "/me")
    buyer_me = api(base, buyer_opener, "GET", "/me")
    if buyer_me.get("wallet_credits") != 288:
        raise DemoError(f"buyer wallet expected 288, got {buyer_me.get('wallet_credits')}")
    if seller_me.get("wallet_credits") != 212:
        raise DemoError(f"seller wallet expected 212, got {seller_me.get('wallet_credits')}")

    sent = api(
        base,
        buyer_opener,
        "POST",
        "/records/messages/send",
        {"to_handle": seller_handle, "body": "面不错"},
    )
    if sent.get("from_kind") != "player":
        raise DemoError(f"send message failed: {sent}")

    print(
        f"  v1.2 run {run_index}: OK seller={seller_handle} buyer={buyer_handle}",
        flush=True,
    )


def run_v14_once(base: str, run_index: int) -> None:
    suffix = uuid.uuid4().hex[:6]
    seller_handle = f"班{suffix[:4]}"
    buyer_handle = f"客{suffix[2:]}"

    seller_jar = CookieJar()
    seller_opener = build_opener(HTTPCookieProcessor(seller_jar))
    buyer_jar = CookieJar()
    buyer_opener = build_opener(HTTPCookieProcessor(buyer_jar))

    api(
        base,
        seller_opener,
        "POST",
        "/auth/register",
        {"handle": seller_handle, "password": PASSWORD},
    )
    api(
        base,
        buyer_opener,
        "POST",
        "/auth/register",
        {"handle": buyer_handle, "password": PASSWORD},
    )
    api(
        base,
        seller_opener,
        "POST",
        "/shop/apply",
        {"display_name": f"当班{run_index}号"},
    )
    offer = api(
        base,
        seller_opener,
        "POST",
        "/shop/offers",
        {
            "item_id": "item_noodle_bowl",
            "display": "当班汤面",
            "price_credits": 10,
        },
    )
    offer_id = offer["id"]
    api(base, seller_opener, "PATCH", "/shop/auto?auto_on=true")

    order = api(
        base,
        buyer_opener,
        "POST",
        "/records/order",
        {"offer_id": offer_id, "in_person": True},
    )
    if order.get("status") != "ready":
        raise DemoError(f"auto_on order should be ready, got {order.get('status')}")
    order_id = order["id"]

    buyer_msgs = api(base, buyer_opener, "GET", "/records/messages")
    if any(m.get("ref_type") == "order" for m in (buyer_msgs.get("messages") or [])):
        raise DemoError("当班+当面：买家不应收到订单通知")

    settled = api(base, buyer_opener, "POST", f"/records/orders/{order_id}/pickup", None)
    if settled.get("status") != "settled":
        raise DemoError(f"pickup expected settled, got {settled.get('status')}")

    print(
        f"  v1.4 run {run_index}: OK auto seller={seller_handle} buyer={buyer_handle}",
        flush=True,
    )


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
        "--v14",
        action="store_true",
        help="Run v1.4 auto_on shop demo",
    )
    parser.add_argument(
        "--v12",
        action="store_true",
        help="Run v1.2 player shop demo instead of v1.0 MVP loop",
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
    if args.v14:
        label = "v1.4 auto"
        runner = run_v14_once
    elif args.v12:
        label = "v1.2 shop"
        runner = run_v12_once
    else:
        label = "v1.0 MVP"
        runner = run_once
    print(f"Smoke demo ({label}): {args.runs} run(s) -> {base}", flush=True)
    for i in range(1, args.runs + 1):
        runner(base, i)
        if i < args.runs and args.pause > 0:
            time.sleep(args.pause)
    print(f"All {args.runs} run(s) passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
