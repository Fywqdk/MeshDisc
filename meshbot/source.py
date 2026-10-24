"""Pick the packet source configured with MESH_SOURCE."""
from __future__ import annotations

import asyncio

from .config import Config
from .mqtt_listener import MqttEvent, run_mqtt


async def run_source(cfg: Config, queue: asyncio.Queue[MqttEvent]) -> None:
    if cfg.source == "tcp":
        if not cfg.mesh_host:
            raise SystemExit("MESH_HOST skal være sat i .env, når MESH_SOURCE=tcp")
        from .tcp_listener import run_tcp

        await run_tcp(cfg, queue)
    elif cfg.source == "mqtt":
        await run_mqtt(cfg, queue)
    else:
        raise SystemExit(f"Ukendt MESH_SOURCE={cfg.source!r} (brug tcp eller mqtt)")
