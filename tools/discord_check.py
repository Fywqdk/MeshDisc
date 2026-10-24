"""Verify the Discord setup: token, server, channel, permissions – and post a test embed.

    python -m tools.discord_check            # check + send test message
    python -m tools.discord_check --no-send  # only check
"""
from __future__ import annotations

import argparse
import sys

import discord

from meshbot.config import Config

REQUIRED = ("view_channel", "send_messages", "embed_links")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-send", action="store_true")
    args = ap.parse_args()
    cfg = Config()
    if not cfg.discord_token:
        sys.exit("✗ DISCORD_TOKEN mangler i .env")

    client = discord.Client(intents=discord.Intents.default())
    result = {"ok": False}

    @client.event
    async def on_ready() -> None:
        try:
            print(f"✓ Logget ind som {client.user} (id {client.user.id})")
            print(f"  Servere: {', '.join(g.name for g in client.guilds) or 'INGEN – botten er ikke inviteret'}")
            print(
                "  Invite-link: https://discord.com/oauth2/authorize"
                f"?client_id={client.user.id}&scope=bot+applications.commands&permissions=19456"
            )
            if not cfg.discord_channel_id:
                print("✗ DISCORD_CHANNEL_ID mangler i .env")
                return
            try:
                ch = client.get_channel(cfg.discord_channel_id) or await client.fetch_channel(cfg.discord_channel_id)
            except (discord.NotFound, discord.Forbidden) as e:
                print(f"✗ Kan ikke se kanal {cfg.discord_channel_id}: {e}")
                return
            print(f"✓ Kanal: #{ch.name} på {ch.guild.name}")
            perms = ch.permissions_for(ch.guild.me)
            missing = [p for p in REQUIRED if not getattr(perms, p)]
            if missing:
                print(f"✗ Mangler rettigheder i kanalen: {', '.join(missing)}")
                return
            print(f"✓ Rettigheder OK ({', '.join(REQUIRED)})")
            if not args.no_send:
                e = discord.Embed(description="Testbesked fra MeshCore-botten ✅", color=0x2ECC71)
                e.set_author(name="discord_check")
                msg = await ch.send(embed=e)
                print(f"✓ Testbesked sendt: {msg.jump_url}")
            result["ok"] = True
        finally:
            await client.close()

    try:
        client.run(cfg.discord_token, log_handler=None)
    except discord.LoginFailure:
        sys.exit("✗ Ugyldigt DISCORD_TOKEN")
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
