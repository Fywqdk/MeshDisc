"""Publish a fake encrypted Public-channel message to MQTT, formatted like an observer.

    python -m tools.send_test_packet "Hej fra testen"
    python -m tools.send_test_packet "Hej" --sender Morten --topic meshcore/AAL/TEST0001/packets

Requires an MQTT user with write access to the topic (e.g. the 'observer' user).
Use --user/--password to override MQTT_USERNAME/MQTT_PASSWORD from .env.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time

import aiomqtt

from meshbot.config import Config
from meshbot.meshcore_decode import Channel, encrypt_grp_txt


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("text")
    ap.add_argument("--sender", default="TestNode")
    ap.add_argument("--channel", default="public", help='"public" eller "navn=hexkey"')
    ap.add_argument("--topic", default="meshcore/TST/TESTOBSERVER/packets")
    ap.add_argument("--user")
    ap.add_argument("--password")
    args = ap.parse_args()
    cfg = Config()

    payload = encrypt_grp_txt(Channel.from_config(args.channel), args.sender, args.text, int(time.time()))
    header = (0x05 << 2) | 0x01  # GRP_TXT, FLOOD
    raw = bytes([header, 1, 0x42]) + payload  # one hop via "42"
    msg = {
        "origin": "test-observer",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "type": "PACKET",
        "direction": "rx",
        "packet_type": "5",
        "route": "F",
        "raw": raw.hex(),
        "SNR": "8.0",
        "RSSI": "-90",
        "hash": raw[-8:].hex(),
    }
    async with aiomqtt.Client(
        cfg.mqtt_host, cfg.mqtt_port,
        username=args.user or cfg.mqtt_username,
        password=args.password or cfg.mqtt_password,
    ) as c:
        await c.publish(args.topic, json.dumps(msg), qos=1)
    print(f"✓ Sendt til {args.topic}: <{args.sender}> {args.text}")


if __name__ == "__main__":
    asyncio.run(main())
