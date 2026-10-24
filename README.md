# MeshCore → Discord bot

Listens to a MeshCore node (directly over TCP, e.g. meshcomod on port 5000, or an observer via MQTT) and reposts packets (by default channel messages from *Public*) to a Discord channel.

## Structure

```
meshbot/
  __main__.py         # entrypoint: python -m meshbot
  config.py           # settings from .env
  source.py           # picks the source from MESH_SOURCE (tcp/mqtt)
  tcp_listener.py     # companion node over TCP (RX log) with auto-reconnect -> asyncio.Queue
  mqtt_listener.py    # aiomqtt client with auto-reconnect -> asyncio.Queue
  meshcore_decode.py  # parses MeshCore packets + decrypts GRP_TXT
  formatters.py       # packet -> Discord embed (add your own handlers here)
  bot.py              # discord.py bot, queue consumer, dedupe, /mesh commands
```

Flow: `TCP/MQTT → queue → parse → filter (POST_TYPES) → dedupe → decrypt → embed → Discord`

## Setup

1. Create a bot at <https://discord.com/developers/applications>, copy the token, and invite it with the scopes `bot` + `applications.commands` and the permissions *Send Messages* / *Embed Links*.
2. Enable *Developer Mode* in Discord, right-click the channel → *Copy Channel ID*.
3. Install and configure:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in token, channel ID and MESH_HOST (or MQTT)
python -m meshbot
```

## Commands

- `/mesh status` – statistics (received, posted, duplicates, queue)
- `/mesh pause` – pause/resume reposting (requires *Manage Channels*)

See [SETUP.md](SETUP.md) for a step-by-step guide (in Danish).

## Observer format (MQTT)

The formatter expects the common meshcore→MQTT layout, where the topic is `meshcore/<IATA>/<pubkey>/packets` and the payload is JSON with a `raw` field (hex of the whole packet) plus optionally `SNR`, `RSSI`, `hash`, `origin`. If your observer publishes differently, adjust `extract_raw_hex()` and the field names in `formatters.py`. Set `POST_RAW=true` and `POST_TYPES=*` to see what actually comes in.

## Extending

- **New packet type:** write a `fmt_xxx(pkt, data, topic)` in `formatters.py` and add it to `HANDLERS`.
- **Private channels:** add `CHANNEL_KEYS=public,Club=<32 hex chars>`.
- **Hashtag channels** (e.g. `#test`): the key is the first 16 bytes of SHA-256 of the channel name including `#`:
  `printf '%s' '#test' | sha256sum | cut -c1-32`
- **Multiple Discord channels / routing:** extend `_consumer()` in `bot.py` to choose a channel based on `pkt.channel` or the topic.

## Note

The packet parser follows the MeshCore packet format (header, path, AES-128-ECB + 2-byte HMAC for group messages). It has been tested against a Heltec V4 running firmware v1.18; test it against your own node, as the path encoding in particular can vary between firmware versions.

## Terms and privacy

- [Terms of Service](TERMS.md)
- [Privacy Policy](PRIVACY.md)

## License

[MIT](LICENSE)
