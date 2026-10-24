"""Discord bot: consumes mesh events (TCP or MQTT) and posts them to a channel."""
from __future__ import annotations

import asyncio
import json
import logging
import time

import discord
from discord import app_commands
from discord.ext import commands

from .config import Config
from .formatters import extract_raw_hex, format_packet, format_raw
from .meshcore_decode import Channel, Packet, decrypt_grp_txt, parse_packet
from .mqtt_listener import MqttEvent
from .source import run_source

log = logging.getLogger(__name__)


class MeshBot(commands.Bot):
    def __init__(self, cfg: Config):
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.cfg = cfg
        self.queue: asyncio.Queue[MqttEvent] = asyncio.Queue(maxsize=1000)
        self.channels = [Channel.from_config(k) for k in cfg.channel_keys]
        self.allowed_types = {t.upper() for t in cfg.post_types}
        self._seen: dict[str, float] = {}
        self.stats = {"rx": 0, "posted": 0, "dupes": 0, "skipped": 0}
        self.paused = False

    async def setup_hook(self) -> None:
        self.loop.create_task(run_source(self.cfg, self.queue))
        self.loop.create_task(self._consumer())
        self.tree.add_command(mesh_group)
        await self.tree.sync()

    async def on_ready(self) -> None:
        log.info("Discord logged in as %s", self.user)

    # ---------------------------------------------------------------- pipeline
    def _is_dupe(self, key: str) -> bool:
        now = time.monotonic()
        self._seen = {k: t for k, t in self._seen.items() if now - t < self.cfg.dedupe_seconds}
        if key in self._seen:
            return True
        self._seen[key] = now
        return False

    def _allowed(self, ptype: str) -> bool:
        return "*" in self.allowed_types or ptype in self.allowed_types

    def _prepare(self, ev: MqttEvent) -> tuple[Packet | None, discord.Embed | None]:
        """Return the parsed packet (if any) and an embed for this event, or None to skip it."""
        raw_hex = extract_raw_hex(ev.data) if ev.data else None
        if not raw_hex:
            if self.cfg.post_raw:
                text = json.dumps(ev.data, indent=1) if ev.data else ev.raw.decode(errors="replace")
                return None, format_raw(ev.topic, text)
            return None, None
        try:
            pkt = parse_packet(bytes.fromhex(raw_hex))
        except (ValueError, IndexError) as e:
            log.debug("Could not parse packet on %s: %s", ev.topic, e)
            return None, None
        if not self._allowed(pkt.payload_type):
            return pkt, None
        # Same packet heard by several observers/paths -> post once
        dedupe_key = (ev.data.get("hash") or "") + pkt.payload.hex()
        if self._is_dupe(dedupe_key):
            self.stats["dupes"] += 1
            return pkt, None
        decrypt_grp_txt(pkt, self.channels)
        return pkt, format_packet(pkt, ev.data, ev.topic)

    def build_embed(self, ev: MqttEvent) -> discord.Embed | None:
        """Return an embed for this event, or None to skip it."""
        return self._prepare(ev)[1]

    def target_channel_id(self, pkt: Packet | None) -> int:
        """Discord channel for a packet: its mesh channel's route, else the default channel."""
        name = (pkt.channel or "").lower() if pkt else ""
        return self.cfg.discord_routes.get(name, self.cfg.discord_channel_id)

    async def _discord_channel(self, channel_id: int) -> discord.abc.Messageable:
        return self.get_channel(channel_id) or await self.fetch_channel(channel_id)

    async def _consumer(self) -> None:
        await self.wait_until_ready()
        for mesh_name, channel_id in self.cfg.discord_routes.items():
            channel = await self._discord_channel(channel_id)
            log.info("Routing #%s to Discord #%s", mesh_name, getattr(channel, "name", channel_id))
        channel = await self._discord_channel(self.cfg.discord_channel_id)
        log.info("Posting everything else to #%s", getattr(channel, "name", channel.id))
        while True:
            ev = await self.queue.get()
            self.stats["rx"] += 1
            if self.paused:
                continue
            try:
                pkt, embed = self._prepare(ev)
                if embed is None:
                    self.stats["skipped"] += 1
                    continue
                channel = await self._discord_channel(self.target_channel_id(pkt))
                await channel.send(embed=embed)  # discord.py handles rate limits
                self.stats["posted"] += 1
            except Exception:
                log.exception("Failed handling event from %s", ev.topic)


# -------------------------------------------------------------- slash commands
mesh_group = app_commands.Group(name="mesh", description="MeshCore bridge")


@mesh_group.command(name="status", description="Vis bridge-statistik")
async def mesh_status(inter: discord.Interaction) -> None:
    bot: MeshBot = inter.client  # type: ignore[assignment]
    s = bot.stats
    await inter.response.send_message(
        f"Kilde: {bot.cfg.source.upper()} · modtaget: {s['rx']} · postet: {s['posted']} · dubletter: {s['dupes']} · "
        f"sprunget over: {s['skipped']} · kø: {bot.queue.qsize()} · "
        f"{'⏸ pauset' if bot.paused else '▶ kører'}",
        ephemeral=True,
    )


@mesh_group.command(name="pause", description="Pause/genoptag reposting")
@app_commands.default_permissions(manage_channels=True)
async def mesh_pause(inter: discord.Interaction) -> None:
    bot: MeshBot = inter.client  # type: ignore[assignment]
    bot.paused = not bot.paused
    await inter.response.send_message("Pauset" if bot.paused else "Genoptaget", ephemeral=True)
