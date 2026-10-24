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

## Channels and routing

`CHANNEL_KEYS` lists the mesh channels the bot decrypts. Messages in other channels are ignored.

```ini
CHANNEL_KEYS=#test,#danmark,Club=00112233445566778899aabbccddeeff
```

- `public` – the default Public channel
- `#name` – a hashtag channel; the key is derived from the name
- `name=<32 hex chars>` – a private channel with its secret key

`DISCORD_ROUTES` sends each mesh channel to its own Discord channel. Anything not listed goes to `DISCORD_CHANNEL_ID`.

```ini
DISCORD_CHANNEL_ID=1563524626397663302
DISCORD_ROUTES=test=1563524626397663302,danmark=1563500000000000000
```

Run `python -m tools.discord_check --no-send` to verify the bot can post in every configured channel.

## Running as a service (Proxmox LXC / Debian)

In a Debian 12 or Ubuntu 24.04 container, as root:

```bash
curl -fsSL https://raw.githubusercontent.com/Fywqdk/MeshDisc/main/deploy/install.sh -o install.sh
bash install.sh
```

The script installs the bot in `/opt/meshdisc` as a systemd service running as the `meshdisc` user. Fill in `/opt/meshdisc/.env`, then:

```bash
systemctl start meshdisc
journalctl -u meshdisc -f
```

To update later, run `bash /opt/meshdisc/deploy/install.sh` again.

## Commands

- `/mesh status` – statistics (received, posted, duplicates, queue)
- `/mesh pause` – pause/resume reposting (requires *Manage Channels*)

See [SETUP.md](SETUP.md) for a step-by-step guide (in Danish).

## Observer format (MQTT)

The formatter expects the common meshcore→MQTT layout, where the topic is `meshcore/<IATA>/<pubkey>/packets` and the payload is JSON with a `raw` field (hex of the whole packet) plus optionally `SNR`, `RSSI`, `hash`, `origin`. If your observer publishes differently, adjust `extract_raw_hex()` and the field names in `formatters.py`. Set `POST_RAW=true` and `POST_TYPES=*` to see what actually comes in.

## Extending

- **New packet type:** write a `fmt_xxx(pkt, data, topic)` in `formatters.py` and add it to `HANDLERS`.
- **Custom routing:** change `target_channel_id()` in `bot.py`, e.g. to route by packet type or topic.

## Note

The packet parser follows the MeshCore packet format (header, path, AES-128-ECB + 2-byte HMAC for group messages). It has been tested against a Heltec V4 running firmware v1.18; test it against your own node, as the path encoding in particular can vary between firmware versions.

## Terms and privacy

- [Terms of Service](TERMS.md)
- [Privacy Policy](PRIVACY.md)

## License

[MIT](LICENSE)
