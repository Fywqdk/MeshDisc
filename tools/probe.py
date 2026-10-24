"""Listen to the mesh source and show what arrives – and what the bot would post.

    python -m tools.probe                 # uses MESH_SOURCE / MESH_* / MQTT_* from .env
    python -m tools.probe --count 20      # stop after 20 messages
    python -m tools.probe --all           # show what would be posted for ALL types

Every message is appended to samples.jsonl so it can be used for tests later.
Discord is NOT contacted.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter

from meshbot.bot import MeshBot
from meshbot.config import Config
from meshbot.formatters import extract_raw_hex
from meshbot.meshcore_decode import decrypt_grp_txt, parse_packet
from meshbot.source import run_source


def describe(bot: MeshBot, ev) -> str:
    lines = [f"\n── {ev.topic}"]
    if ev.data is None:
        lines.append(f"   (ikke JSON) {ev.raw[:200]!r}")
        return "\n".join(lines)
    lines.append(f"   felter: {', '.join(sorted(ev.data))}")
    raw_hex = extract_raw_hex(ev.data)
    if not raw_hex:
        lines.append("   intet raw-felt → ignoreres af botten (medmindre POST_RAW=true)")
        return "\n".join(lines)
    try:
        pkt = parse_packet(bytes.fromhex(raw_hex))
    except Exception as e:  # noqa: BLE001
        lines.append(f"   ⚠ kunne ikke parse raw: {e}")
        return "\n".join(lines)
    lines.append(f"   pakke: {pkt.payload_type} / {pkt.route_type}, path={pkt.path}, {len(pkt.payload)} B payload")
    if decrypt_grp_txt(pkt, bot.channels):
        lines.append(f"   🔓 #{pkt.channel} <{pkt.sender}> {pkt.text}")
    elif pkt.payload_type == "GRP_TXT":
        lines.append("   🔒 ukendt kanal (nøgle mangler i CHANNEL_KEYS)")
    embed = bot.build_embed(ev)
    if embed:
        d = embed.to_dict()
        lines.append(f"   → Discord: {d.get('author', {}).get('name') or d.get('title')}: {d.get('description', '')[:120]}")
    return "\n".join(lines)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=0, help="stop efter N beskeder (0 = uendeligt)")
    ap.add_argument("--all", action="store_true", help="vis Discord-output for alle pakketyper")
    ap.add_argument("--out", default="samples.jsonl")
    args = ap.parse_args()

    cfg = Config()
    if args.all:
        cfg.post_types = ["*"]
    bot = MeshBot(cfg)
    task = asyncio.create_task(run_source(cfg, bot.queue))
    if cfg.source == "tcp":
        print(f"Lytter på MeshCore-node {cfg.mesh_host}:{cfg.mesh_port} (TCP) … (Ctrl+C for stop)")
    else:
        print(f"Lytter på {cfg.mqtt_host}:{cfg.mqtt_port} topics={cfg.mqtt_topics} … (Ctrl+C for stop)")
    types: Counter[str] = Counter()
    n = 0
    try:
        with open(args.out, "a", encoding="utf-8") as f:
            while not args.count or n < args.count:
                ev = await bot.queue.get()
                n += 1
                f.write(json.dumps({"topic": ev.topic, "payload": ev.raw.decode(errors="replace")}) + "\n")
                f.flush()
                print(describe(bot, ev))
                types[ev.topic.rsplit("/", 1)[-1]] += 1
    finally:
        task.cancel()
        print(f"\n{n} beskeder · pr. topic-endelse: {dict(types)} · gemt i {args.out}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
