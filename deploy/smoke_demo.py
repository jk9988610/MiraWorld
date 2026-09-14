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
from urllib.parse import quote
from urllib.request import HTTPCookieProcessor, Request, build_opener

DEFAULT_BASE = "http://8.133.252.224/miraworld/api"
CITY = "潮灯市"
SPOT = "spot_sunset"
OFFER = "offer_standard_noodle"
PASSWORD = "SmokeDemo1!"


class DemoError(RuntimeError):
    pass


def run_v20_once(base: str, run_index: int) -> None:
    tick_secret = os.environ.get("MIRAWORLD_TICK_SECRET", "dev-tick-secret")
    opener = build_opener()

    health = api(base, opener, "GET", "/health")
    if not health.get("ok"):
        raise DemoError(f"health check failed: {health}")

    status = api(base, opener, "GET", f"/economy/status?city={quote(CITY)}")
    if not status.get("institutions"):
        raise DemoError(f"economy not seeded: {status}")
    if status.get("pop_groups", {}).get("count", 0) < 10:
        raise DemoError(f"expected 10 pop groups, got {status.get('pop_groups')}")

    tick = api(
        base,
        opener,
        "POST",
        f"/economy/tick?city={quote(CITY)}&force=1",
        None,
        extra_headers={"X-Tick-Secret": tick_secret},
    )
    if not tick.get("ok"):
        raise DemoError(f"tick failed: {tick}")
    purchases = (tick.get("summary") or {}).get("purchases", {}).get("count", 0)
    if purchases < 1:
        raise DemoError(f"expected pop purchases, got {tick}")

    spotlight = api(base, opener, "GET", "/economy/institutions/inst_chen_noodle/spotlight")
    items = spotlight.get("items") or []
    if not items:
        raise DemoError(f"expected spotlight entries, got {spotlight}")
    if len(items) > 10:
        raise DemoError(f"spotlight max 10, got {len(items)}")
    name = items[0].get("display_name", "")
    job = items[0].get("job_display", "")
    if not job:
        raise DemoError(f"spotlight missing job_display: {items[0]}")
    if not name.endswith(job):
        raise DemoError(f"spotlight name should be surname+job: {name!r} / {job!r}")
    if name.endswith("先生") or name.endswith("女士"):
        raise DemoError(f"spotlight must not use honorific: {name!r}")

    audit = api(base, opener, "GET", f"/economy/audit?city={quote(CITY)}")
    if not audit.get("ok"):
        raise DemoError(f"economy audit failed: {audit}")
    wallets = (audit.get("checks") or {}).get("wallets") or {}
    if wallets.get("unemployed_groups", 0) < 1:
        raise DemoError(f"expected unemployed pop groups for P3: {wallets}")
    if wallets.get("employed_groups", 0) < 1:
        raise DemoError(f"expected employed pop groups for P3: {wallets}")

    print(
        f"  v2.0 run {run_index}: OK purchases={purchases} spotlight={len(items)} audit=ok",
        flush=True,
    )


def run_v22_once(base: str, run_index: int) -> None:
    tick_secret = os.environ.get("MIRAWORLD_TICK_SECRET", "dev-tick-secret")
    opener = build_opener()

    hub = api(base, opener, "GET", f"/economy/hub?city={quote(CITY)}")
    resources = hub.get("resources") or []
    if len(resources) < 5:
        raise DemoError(f"expected 5 hub resources, got {hub}")

    tick = api(
        base,
        opener,
        "POST",
        f"/economy/tick?city={quote(CITY)}&force=1",
        None,
        extra_headers={"X-Tick-Secret": tick_secret},
    )
    if not tick.get("ok"):
        raise DemoError(f"tick failed: {tick}")
    summary = tick.get("summary") or {}
    production = summary.get("production") or {}
    if int(production.get("items", 0)) < 1:
        raise DemoError(f"expected production items, got {production}")
    purchases = (summary.get("purchases") or {}).get("count", 0)
    procurement = (summary.get("procurement") or {}).get("count", 0)
    if purchases < 1 and procurement < 1:
        raise DemoError(f"expected market purchases or procurement, got {summary}")

    status = api(base, opener, "GET", f"/economy/status?city={quote(CITY)}")
    groups = (status.get("pop_groups") or {}).get("groups") or []
    if not any(int(g.get("satisfaction", 0)) > 0 for g in groups):
        if procurement < 1:
            raise DemoError(f"expected pop satisfaction or procurement: {status}")

    audit = api(base, opener, "GET", f"/economy/audit?city={quote(CITY)}")
    if not audit.get("ok"):
        raise DemoError(f"economy audit failed: {audit}")

    print(
        f"  v2.2 run {run_index}: OK production={production.get('items')} "
        f"purchases={purchases} procurement={procurement}",
        flush=True,
    )


def run_v21_once(base: str, run_index: int) -> None:
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    handle = f"资{run_index:02d}{uuid.uuid4().hex[:4]}"

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

    status = api(base, opener, "GET", "/capital/status")
    if not status.get("can_claim_today"):
        raise DemoError(f"expected can_claim_today: {status}")
    assets = status.get("assets") or {}
    if int(assets.get("total", 0)) < 300:
        raise DemoError(f"unexpected asset total: {assets}")

    claim = api(base, opener, "POST", "/capital/daily-investment", None)
    grant = claim.get("grant") or {}
    amount = int(grant.get("amount", 0))
    base_cfg = int((status.get("config") or {}).get("daily_investment_base", 200000))
    if amount < base_cfg:
        raise DemoError(f"daily investment below base: {amount} < {base_cfg}")
    wallet = int(claim.get("wallet_credits", 0))
    if wallet != 300 + amount:
        raise DemoError(f"wallet after grant expected {300 + amount}, got {wallet}")

    try:
        api(base, opener, "POST", "/capital/daily-investment", None)
        raise DemoError("second claim should fail")
    except DemoError as exc:
        if "409" not in str(exc):
            raise

    company = api(
        base,
        opener,
        "POST",
        "/capital/company",
        {"display_name": f"资{run_index}号公司"},
    )
    if not company.get("id"):
        raise DemoError(f"company create failed: {company}")

    deposit = api(
        base,
        opener,
        "POST",
        "/capital/company/transfer",
        {"direction": "to_company", "amount": 1000},
    )
    if int(deposit.get("company_wallet", 0)) < 1000:
        raise DemoError(f"company deposit failed: {deposit}")
    withdraw = api(
        base,
        opener,
        "POST",
        "/capital/company/transfer",
        {"direction": "to_player", "amount": 500},
    )
    if int(withdraw.get("company_wallet", 0)) != 500:
        raise DemoError(f"company withdraw failed: {withdraw}")

    print(
        f"  v2.1 run {run_index}: OK grant={amount} transfer company={company.get('display_name')}",
        flush=True,
    )


def api(base: str, opener, method: str, path: str, body: dict | None = None, extra_headers: dict | None = None) -> dict:
    url = f"{base.rstrip('/')}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
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
    if not order_msgs:
        raise DemoError("点面后应有订单通知")

    summary = api(base, opener, "GET", "/records/messages/summary")
    if "unread_count" not in summary:
        raise DemoError(f"messages summary missing unread_count: {summary}")

    consumed = api(base, opener, "POST", "/stacks/item_noodle_bowl/consume", None)
    if consumed.get("qty", 1) != 0:
        raise DemoError(f"consume expected qty 0, got {consumed}")

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

    order = api(base, buyer_opener, "POST", "/records/order", {"offer_id": offer_id})
    if order.get("status") != "escrowed":
        raise DemoError(f"player order should be escrowed, got {order.get('status')}")
    order_id = order["id"]

    accepted = api(base, seller_opener, "POST", f"/records/orders/{order_id}/accept", None)
    if accepted.get("status") != "processing":
        raise DemoError(f"accept expected processing, got {accepted.get('status')}")

    ready = api(base, seller_opener, "POST", f"/records/orders/{order_id}/ready", None)
    if ready.get("status") != "ready":
        raise DemoError(f"ready expected ready, got {ready.get('status')}")

    buyer_msgs = api(base, buyer_opener, "GET", "/records/messages")
    if not any(m.get("ref_type") == "order" for m in (buyer_msgs.get("messages") or [])):
        raise DemoError("标记好了后买家应收到订单通知")

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
        {"offer_id": offer_id},
    )
    if order.get("status") != "ready":
        raise DemoError(f"auto_on order should be ready, got {order.get('status')}")
    order_id = order["id"]

    buyer_msgs = api(base, buyer_opener, "GET", "/records/messages")
    if not any(m.get("ref_type") == "order" for m in (buyer_msgs.get("messages") or [])):
        raise DemoError("当班自动好了：买家应收到订单通知")

    settled = api(base, buyer_opener, "POST", f"/records/orders/{order_id}/pickup", None)
    if settled.get("status") != "settled":
        raise DemoError(f"pickup expected settled, got {settled.get('status')}")

    print(
        f"  v1.4 run {run_index}: OK auto seller={seller_handle} buyer={buyer_handle}",
        flush=True,
    )


def run_v15_once(base: str, run_index: int) -> None:
    suffix = uuid.uuid4().hex[:6]
    issuer_handle = f"委{suffix[:4]}"
    worker_handle = f"接{suffix[2:]}"

    issuer_jar = CookieJar()
    issuer_opener = build_opener(HTTPCookieProcessor(issuer_jar))
    worker_jar = CookieJar()
    worker_opener = build_opener(HTTPCookieProcessor(worker_jar))

    api(
        base,
        issuer_opener,
        "POST",
        "/auth/register",
        {"handle": issuer_handle, "password": PASSWORD},
    )
    api(
        base,
        worker_opener,
        "POST",
        "/auth/register",
        {"handle": worker_handle, "password": PASSWORD},
    )

    bounty = api(
        base,
        issuer_opener,
        "POST",
        "/bounties",
        {
            "kind": "buy",
            "item_id": "item_mist_snack",
            "qty": 3,
            "price_credits": 50,
        },
    )
    if bounty.get("status") != "open":
        raise DemoError(f"bounty should be open, got {bounty.get('status')}")
    if bounty.get("kind") != "buy":
        raise DemoError(f"expected buy bounty, got {bounty.get('kind')}")
    bounty_id = bounty["id"]

    issuer_after_create = api(base, issuer_opener, "GET", "/me")
    if issuer_after_create.get("wallet_credits") != 250:
        raise DemoError(
            f"issuer wallet expected 250 after escrow, got {issuer_after_create.get('wallet_credits')}"
        )

    taken = api(base, worker_opener, "POST", f"/bounties/{bounty_id}/take", None)
    if taken.get("status") != "taken":
        raise DemoError(f"take expected taken, got {taken.get('status')}")

    issuer_msgs = api(base, issuer_opener, "GET", "/records/messages")
    if not any(m.get("ref_type") == "bounty" for m in (issuer_msgs.get("messages") or [])):
        raise DemoError("委托：发单人应收到接单通知")

    submitted = api(base, worker_opener, "POST", f"/bounties/{bounty_id}/submit", None)
    if submitted.get("status") != "submitted":
        raise DemoError(f"submit expected submitted, got {submitted.get('status')}")

    settled = api(base, issuer_opener, "POST", f"/bounties/{bounty_id}/settle", None)
    if settled.get("status") != "settled":
        raise DemoError(f"settle expected settled, got {settled.get('status')}")

    worker_me = api(base, worker_opener, "GET", "/me")
    issuer_me = api(base, issuer_opener, "GET", "/me")
    if worker_me.get("wallet_credits") != 350:
        raise DemoError(f"worker wallet expected 350, got {worker_me.get('wallet_credits')}")
    if issuer_me.get("wallet_credits") != 250:
        raise DemoError(f"issuer wallet expected 250, got {issuer_me.get('wallet_credits')}")

    cancel_bounty = api(
        base,
        issuer_opener,
        "POST",
        "/bounties",
        {
            "kind": "sell",
            "item_id": "item_noodle_bowl",
            "qty": 2,
            "price_credits": 20,
        },
    )
    cancel_id = cancel_bounty["id"]
    if cancel_bounty.get("kind") != "sell":
        raise DemoError(f"expected sell bounty, got {cancel_bounty.get('kind')}")
    cancelled = api(base, issuer_opener, "POST", f"/bounties/{cancel_id}/cancel", None)
    if cancelled.get("status") != "cancelled":
        raise DemoError(f"cancel expected cancelled, got {cancelled.get('status')}")
    issuer_after_cancel = api(base, issuer_opener, "GET", "/me")
    if issuer_after_cancel.get("wallet_credits") != 250:
        raise DemoError(
            f"issuer wallet expected 250 after cancel refund, got {issuer_after_cancel.get('wallet_credits')}"
        )

    for i in range(10):
        api(
            base,
            issuer_opener,
            "POST",
            "/bounties",
            {
                "kind": "buy" if i % 2 == 0 else "sell",
                "item_id": "item_noodle_bowl",
                "qty": 1,
                "price_credits": 5,
            },
        )
    try:
        api(
            base,
            issuer_opener,
            "POST",
            "/bounties",
            {"kind": "buy", "item_id": "item_noodle_bowl", "qty": 1, "price_credits": 5},
        )
    except DemoError:
        pass
    else:
        raise DemoError("11th open bounty should be rejected")

    print(
        f"  v1.5 run {run_index}: OK issuer={issuer_handle} worker={worker_handle}",
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
        "--v22",
        action="store_true",
        help="Run v2.2 two-layer hub + production demo",
    )
    parser.add_argument(
        "--v21",
        action="store_true",
        help="Run v2.1 daily investment + company demo",
    )
    parser.add_argument(
        "--v20",
        action="store_true",
        help="Run v2.0 economy tick demo",
    )
    parser.add_argument(
        "--v15",
        action="store_true",
        help="Run v1.5 bounty demo",
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
    if args.v22:
        label = "v2.2 two-layer"
        runner = run_v22_once
    elif args.v21:
        label = "v2.1 capital"
        runner = run_v21_once
    elif args.v20:
        label = "v2.0 economy"
        runner = run_v20_once
    elif args.v15:
        label = "v1.5 bounty"
        runner = run_v15_once
    elif args.v14:
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
