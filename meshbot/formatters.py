"""Turn MQTT events into Discord embeds.

The observer format assumed here is the common meshcore-to-MQTT bridge layout:

    topic:   meshcore/<IATA>/<observer_pubkey>/packets
    payload: {"origin": "...", "timestamp": "...", "type": "PACKET",
              "packet_type": "5", "route": "F", "raw": "<hex>",
              "SNR": "7.5", "RSSI": "-92", "hash": "...", ...}

Adjust `extract_raw_hex()` / field names if your observer publishes differently.
Add new handlers to HANDLERS to support more payload types.
"""
from __future__ import annotations

import datetime as dt
from typing import Callable

import discord

from .meshcore_decode import Packet

COLORS = {"GRP_TXT": 0x2ECC71, "ADVERT": 0x3498DB, "TXT_MSG": 0x9B59B6}


def extract_raw_hex(data: dict) -> str | None:
    for key in ("raw", "raw_hex", "data", "packet"):
        v = data.get(key)
        if isinstance(v, str) and v:
            return v
    return None


def observer_from_topic(topic: str, data: dict) -> str:
    parts = topic.split("/")
    region = parts[1] if len(parts) > 2 else "?"
    origin = data.get("origin") or (parts[2][:8] if len(parts) > 2 else "?")
    return f"{origin} ({region})"


def _footer(e: discord.Embed, pkt: Packet, data: dict, topic: str) -> discord.Embed:
    bits = [f"via {observer_from_topic(topic, data)}"]
    if data.get("SNR") is not None:
        bits.append(f"SNR {data['SNR']}")
    if data.get("RSSI") is not None:
        bits.append(f"RSSI {data['RSSI']}")
    bits.append(f"{len(pkt.path)} hops")
    e.set_footer(text=" · ".join(bits))
    return e


def fmt_grp_txt(pkt: Packet, data: dict, topic: str) -> discord.Embed | None:
    if pkt.text is None:
        return None  # couldn't decrypt – unknown channel
    e = discord.Embed(
        description=pkt.text[:4000],
        color=COLORS["GRP_TXT"],
        timestamp=dt.datetime.fromtimestamp(pkt.sent_at, dt.timezone.utc) if pkt.sent_at else None,
    )
    e.set_author(name=f"{pkt.sender or 'Ukendt'}  ·  #{pkt.channel}")
    return _footer(e, pkt, data, topic)


def fmt_generic(pkt: Packet, data: dict, topic: str) -> discord.Embed:
    e = discord.Embed(
        title=f"{pkt.payload_type} ({pkt.route_type})",
        description=f"Path: `{' → '.join(pkt.path) or 'direkte'}`\nPayload: {len(pkt.payload)} bytes",
        color=COLORS.get(pkt.payload_type, 0x95A5A6),
    )
    return _footer(e, pkt, data, topic)


Handler = Callable[[Packet, dict, str], "discord.Embed | None"]
HANDLERS: dict[str, Handler] = {
    "GRP_TXT": fmt_grp_txt,
    # "ADVERT": fmt_advert,   # <- add your own here
}


def format_packet(pkt: Packet, data: dict, topic: str) -> discord.Embed | None:
    return HANDLERS.get(pkt.payload_type, fmt_generic)(pkt, data, topic)


def format_raw(topic: str, text: str) -> discord.Embed:
    return discord.Embed(title=topic[:256], description=f"```{text[:3900]}```", color=0x7F8C8D)
