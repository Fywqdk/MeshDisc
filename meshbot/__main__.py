import logging

from .bot import MeshBot
from .config import Config


def main() -> None:
    cfg = Config()
    if not cfg.discord_token or not cfg.discord_channel_id:
        raise SystemExit("DISCORD_TOKEN og DISCORD_CHANNEL_ID skal være sat i .env")
    if cfg.source == "tcp" and not cfg.mesh_host:
        raise SystemExit("MESH_HOST (nodens IP) skal være sat i .env, når MESH_SOURCE=tcp")
    logging.basicConfig(
        level=cfg.log_level.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    MeshBot(cfg).run(cfg.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
