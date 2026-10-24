"""MQTT listener: subscribes to the MeshCore observer and pushes events to a queue."""
from __future__ import annotations

import asyncio
import json
import logging
import ssl
from dataclasses import dataclass
from typing import Any

import aiomqtt

from .config import Config

log = logging.getLogger(__name__)


@dataclass
class MqttEvent:
    topic: str
    data: dict[str, Any] | None  # parsed JSON, or None if payload wasn't JSON
    raw: bytes


async def run_mqtt(cfg: Config, queue: asyncio.Queue[MqttEvent]) -> None:
    """Connect, subscribe and forward messages forever (auto-reconnect)."""
    tls = ssl.create_default_context() if cfg.mqtt_tls else None
    backoff = 1
    while True:
        try:
            async with aiomqtt.Client(
                hostname=cfg.mqtt_host,
                port=cfg.mqtt_port,
                username=cfg.mqtt_username,
                password=cfg.mqtt_password,
                identifier=cfg.mqtt_client_id,
                tls_context=tls,
            ) as client:
                for topic in cfg.mqtt_topics:
                    await client.subscribe(topic)
                log.info("MQTT connected to %s:%s, topics=%s", cfg.mqtt_host, cfg.mqtt_port, cfg.mqtt_topics)
                backoff = 1
                async for msg in client.messages:
                    raw = bytes(msg.payload) if msg.payload is not None else b""
                    try:
                        data = json.loads(raw)
                        if not isinstance(data, dict):
                            data = {"value": data}
                    except (ValueError, UnicodeDecodeError):
                        data = None
                    await queue.put(MqttEvent(str(msg.topic), data, raw))
        except aiomqtt.MqttError as e:
            log.warning("MQTT error: %s – reconnecting in %ss", e, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
