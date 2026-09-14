"""米拉世界 MiraWorld API."""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth_util import JWT_SECRET
from db import init_db
from routers import auth, bounties, capital, catalog, economy, me, records, shop, stacks, world, world_gate

app = FastAPI(title="米拉世界 MiraWorld", version="1.0.0-mvp")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(me.router)
app.include_router(world.router)
app.include_router(catalog.router)
app.include_router(records.router)
app.include_router(shop.router)
app.include_router(bounties.router)
app.include_router(stacks.router)
app.include_router(economy.router)
app.include_router(capital.router)
app.include_router(world_gate.router)


@app.on_event("startup")
def on_startup() -> None:
    if JWT_SECRET == "dev-secret-change-me" and os.environ.get("MIRAWORLD_ENV") == "production":
        raise RuntimeError("Set MIRAWORLD_JWT_SECRET in production")
    init_db()


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}
