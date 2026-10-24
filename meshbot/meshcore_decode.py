"""Minimal MeshCore packet decoder.

Decodes the packet header and (optionally) decrypts GRP_TXT channel messages
when the channel secret is known.

Packet layout (MeshCore over-the-air):
    [header:1][transport_codes:4 if TRANSPORT_*][path_len:1][path:N][payload...]

    header bits: 0-1 route type, 2-5 payload type, 6-7 payload version

GRP_TXT payload:
    [channel_hash:1][mac:2][ciphertext (AES-128-ECB)]
    plaintext: [timestamp:4 LE][flags:1]["sender: message"\0...]

NOTE: Newer firmware may encode hash size in the upper bits of path_len
(multi-byte path hashes). This decoder handles that, but verify against the
firmware version your mesh runs.
"""
from __future__ import annotations

import hashlib
import hmac
import struct
from dataclasses import dataclass, field

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Well-known secret for the default "Public" channel
PUBLIC_CHANNEL_KEY = "8b3387e9c5cdea6ac9e5edbaa115cd72"

ROUTE_TYPES = {0: "TRANSPORT_FLOOD", 1: "FLOOD", 2: "DIRECT", 3: "TRANSPORT_DIRECT"}
PAYLOAD_TYPES = {
    0x00: "REQ", 0x01: "RESPONSE", 0x02: "TXT_MSG", 0x03: "ACK",
    0x04: "ADVERT", 0x05: "GRP_TXT", 0x06: "GRP_DATA", 0x07: "ANON_REQ",
    0x08: "PATH", 0x09: "TRACE", 0x0A: "MULTIPART", 0x0F: "RAW_CUSTOM",
}


@dataclass
class Channel:
    name: str
    secret: bytes  # 16 bytes

    @property
    def hash_byte(self) -> int:
        return hashlib.sha256(self.secret).digest()[0]

    @classmethod
    def from_config(cls, value: str) -> "Channel":
        # Accept "public", "hexkey" or "name=hexkey"
        name, _, key = value.rpartition("=")
        if key.lower() == "public":
            return cls(name or "Public", bytes.fromhex(PUBLIC_CHANNEL_KEY))
        return cls(name or f"ch-{key[:4]}", bytes.fromhex(key))


@dataclass
class Packet:
    route_type: str
    payload_type: str
    version: int
    path: list[str] = field(default_factory=list)
    payload: bytes = b""
    # Filled for decrypted GRP_TXT
    channel: str | None = None
    sender: str | None = None
    text: str | None = None
    sent_at: int | None = None


def parse_packet(raw: bytes) -> Packet:
    header = raw[0]
    route = header & 0x03
    ptype = (header >> 2) & 0x0F
    version = (header >> 6) & 0x03
    i = 1
    if route in (0, 3):  # transport codes present
        i += 4
    path_len_byte = raw[i]
    i += 1
    hash_size = ((path_len_byte >> 6) & 0x03) + 1
    hop_count = path_len_byte & 0x3F
    path_bytes = raw[i : i + hop_count * hash_size]
    i += len(path_bytes)
    path = [path_bytes[j : j + hash_size].hex() for j in range(0, len(path_bytes), hash_size)]
    return Packet(
        route_type=ROUTE_TYPES.get(route, str(route)),
        payload_type=PAYLOAD_TYPES.get(ptype, f"0x{ptype:02X}"),
        version=version,
        path=path,
        payload=raw[i:],
    )


def decrypt_grp_txt(pkt: Packet, channels: list[Channel]) -> bool:
    """Try to decrypt a GRP_TXT packet in-place. Returns True on success."""
    if pkt.payload_type != "GRP_TXT" or len(pkt.payload) < 3 + 16:
        return False
    ch_hash, mac, ct = pkt.payload[0], pkt.payload[1:3], pkt.payload[3:]
    for ch in channels:
        if ch.hash_byte != ch_hash:
            continue
        hmac_key = ch.secret.ljust(32, b"\x00")
        if hmac.new(hmac_key, ct, hashlib.sha256).digest()[:2] != mac:
            continue
        if len(ct) % 16:
            continue
        dec = Cipher(algorithms.AES(ch.secret), modes.ECB()).decryptor()
        plain = dec.update(ct) + dec.finalize()
        ts = struct.unpack_from("<I", plain, 0)[0]
        body = plain[5:].split(b"\x00", 1)[0].decode("utf-8", errors="replace")
        sender, sep, text = body.partition(": ")
        pkt.channel = ch.name
        pkt.sent_at = ts
        pkt.sender, pkt.text = (sender, text) if sep else (None, body)
        return True
    return False


def encrypt_grp_txt(channel: Channel, sender: str, text: str, ts: int = 0) -> bytes:
    """Build a GRP_TXT payload (used for tests / future sending support)."""
    plain = struct.pack("<IB", ts, 0) + f"{sender}: {text}".encode()
    plain += b"\x00" * (-len(plain) % 16)
    enc = Cipher(algorithms.AES(channel.secret), modes.ECB()).encryptor()
    ct = enc.update(plain) + enc.finalize()
    mac = hmac.new(channel.secret.ljust(32, b"\x00"), ct, hashlib.sha256).digest()[:2]
    return bytes([channel.hash_byte]) + mac + ct
