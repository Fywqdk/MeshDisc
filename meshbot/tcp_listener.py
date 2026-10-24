"""TCP listener: connects to a MeshCore companion node (e.g. meshcomod on port 5000).

The node pushes an "RX log" frame for every packet it hears over the air
(SNR, RSSI and the raw packet). We turn each one into the same event the MQTT
listener produces, so the rest of the pipeline (parse -> filter -> dedupe ->
decrypt -> Discord) is unchanged.

Only the RX log is read. The bot never syncs the node's message queue, so the
phone app still receives every message as usual.
"""
from __future__ import annotations

import asyncio
import json
import logging

from meshcore import EventType, MeshCore

from .config import Config
from .mqtt_listener import MqttEvent

log = logging.getLogger(__name__)

KEEPALIVE_SECONDS = 60


async def run_tcp(cfg: Config, queue: asyncio.Queue[MqttEvent]) -> None:
    """Connect to the node and forward RX log packets forever (auto-reconnect)."""
    backoff = 1
    while True:
        mc: MeshCore | None = None
        try:
            mc = await asyncio.wait_for(MeshCore.create_tcp(cfg.mesh_host, cfg.mesh_port), timeout=15)
            if mc is None:
                raise ConnectionError("noden svarede ikke på APP_START")
            name = (mc.self_info or {}).get("name") or cfg.mesh_host
            topic = f"meshcore/TCP/{name}/packets"
            lost = asyncio.Event()

            async def on_rx(ev) -> None:
                p = ev.payload or {}
                if not p.get("payload"):
                    return
                data = {
                    "origin": name,
                    "raw": p["payload"],
                    "SNR": p.get("snr"),
                    "RSSI": p.get("rssi"),
                }
                try:
                    queue.put_nowait(MqttEvent(topic, data, json.dumps(data).encode()))
                except asyncio.QueueFull:
                    log.warning("Kø fuld – dropper pakke")

            async def on_disconnect(_ev) -> None:
                lost.set()

            mc.subscribe(EventType.RX_LOG_DATA, on_rx)
            mc.subscribe(EventType.DISCONNECTED, on_disconnect)
            log.info("Forbundet til MeshCore-node %r på %s:%s", name, cfg.mesh_host, cfg.mesh_port)
            backoff = 1

            # Wait for a disconnect; poke the node now and then so a dead
            # Wi-Fi link is noticed even if the socket never closes.
            while not lost.is_set():
                try:
                    await asyncio.wait_for(lost.wait(), timeout=KEEPALIVE_SECONDS)
                except asyncio.TimeoutError:
                    res = await mc.commands.send_device_query()
                    if res is None or res.type == EventType.ERROR:
                        log.warning("Noden svarer ikke på keepalive")
                        break
            log.warning("Forbindelsen til noden er tabt")
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 – OSError, timeout, protocol errors …
            log.warning("TCP-fejl mod %s:%s: %s", cfg.mesh_host, cfg.mesh_port, e or type(e).__name__)
        finally:
            if mc is not None:
                try:
                    await mc.disconnect()
                except Exception:  # noqa: BLE001
                    pass
        log.info("Prøver igen om %ss", backoff)
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60)
