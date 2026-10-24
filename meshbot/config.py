"""Configuration loaded from environment variables / .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _list(name: str, default: str = "") -> list[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


@dataclass
class Config:
    # Discord
    discord_token: str = field(default_factory=lambda: os.getenv("DISCORD_TOKEN", ""))
    discord_channel_id: int = field(default_factory=lambda: int(os.getenv("DISCORD_CHANNEL_ID") or 0))

    # Where packets come from: "tcp" (companion node, e.g. meshcomod) or "mqtt" (observer via broker)
    source: str = field(default_factory=lambda: os.getenv("MESH_SOURCE", "tcp").strip().lower())
    mesh_host: str = field(default_factory=lambda: os.getenv("MESH_HOST", ""))
    mesh_port: int = field(default_factory=lambda: int(os.getenv("MESH_PORT", "5000")))

    # MQTT
    mqtt_host: str = field(default_factory=lambda: os.getenv("MQTT_HOST", "localhost"))
    mqtt_port: int = field(default_factory=lambda: int(os.getenv("MQTT_PORT", "1883")))
    mqtt_username: str | None = field(default_factory=lambda: os.getenv("MQTT_USERNAME") or None)
    mqtt_password: str | None = field(default_factory=lambda: os.getenv("MQTT_PASSWORD") or None)
    mqtt_tls: bool = field(default_factory=lambda: _bool("MQTT_TLS"))
    mqtt_client_id: str = field(default_factory=lambda: os.getenv("MQTT_CLIENT_ID", "meshcore-discord-bot"))
    mqtt_topics: list[str] = field(default_factory=lambda: _list("MQTT_TOPICS", "meshcore/#"))

    # Behaviour
    # Which MeshCore payload types to post: e.g. "GRP_TXT,ADVERT" or "*" for everything
    post_types: list[str] = field(default_factory=lambda: _list("POST_TYPES", "GRP_TXT"))
    # Channel secrets (hex, 16 bytes) used to decrypt group messages. "public" = default Public channel key.
    channel_keys: list[str] = field(default_factory=lambda: _list("CHANNEL_KEYS", "public"))
    # Seconds to remember packet hashes (dedupe when several observers hear the same packet)
    dedupe_seconds: int = field(default_factory=lambda: int(os.getenv("DEDUPE_SECONDS", "60")))
    # Post raw/unknown MQTT messages too (handy while debugging)
    post_raw: bool = field(default_factory=lambda: _bool("POST_RAW"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
