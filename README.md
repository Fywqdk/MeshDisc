# MeshCore → Discord bot

Lytter på en MeshCore-node (direkte via TCP, fx meshcomod på port 5000, eller en observer via MQTT) og reposter pakker (som standard kanalbeskeder fra *Public*) i en Discord-kanal.

## Struktur

```
meshbot/
  __main__.py         # entrypoint: python -m meshbot
  config.py           # indstillinger fra .env
  source.py           # vælger kilde ud fra MESH_SOURCE (tcp/mqtt)
  tcp_listener.py     # companion-node over TCP (RX log) med auto-reconnect -> asyncio.Queue
  mqtt_listener.py    # aiomqtt-klient med auto-reconnect -> asyncio.Queue
  meshcore_decode.py  # parser MeshCore-pakker + dekrypterer GRP_TXT
  formatters.py       # pakke -> Discord embed (tilføj egne handlers her)
  bot.py              # discord.py bot, kø-consumer, dedupe, /mesh-kommandoer
```

Flow: `TCP/MQTT → queue → parse → filter (POST_TYPES) → dedupe → dekrypter → embed → Discord`

## Opsætning

1. Opret en bot på <https://discord.com/developers/applications>, kopiér token, og invitér den med scopes `bot` + `applications.commands` og rettigheden *Send Messages* / *Embed Links*.
2. Slå *Developer Mode* til i Discord, højreklik kanalen → *Copy Channel ID*.
3. Installer og konfigurer:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # udfyld token, kanal-id og MESH_HOST (eller MQTT)
python -m meshbot
```

## Kommandoer

- `/mesh status` – statistik (modtaget, postet, dubletter, kø)
- `/mesh pause` – pause/genoptag reposting (kræver *Manage Channels*)

Se [SETUP.md](SETUP.md) for en trin-for-trin-guide.

## Observer-format (MQTT)

Formatteren forventer det udbredte meshcore→MQTT-layout, hvor topic er `meshcore/<IATA>/<pubkey>/packets` og payload er JSON med et `raw`-felt (hex af hele pakken) samt evt. `SNR`, `RSSI`, `hash`, `origin`. Publicerer din observer anderledes, så ret `extract_raw_hex()` og feltnavnene i `formatters.py`. Sæt `POST_RAW=true` og `POST_TYPES=*` for at se hvad der faktisk kommer ind.

## Udvidelse

- **Ny pakketype:** skriv en `fmt_xxx(pkt, data, topic)` i `formatters.py` og tilføj den i `HANDLERS`.
- **Private kanaler:** tilføj `CHANNEL_KEYS=public,Klub=<32 hex-tegn>`.
- **Flere Discord-kanaler / routing:** udvid `_consumer()` i `bot.py` til at vælge kanal ud fra `pkt.channel` eller topic.

## Bemærk

Pakkeparseren er skrevet efter MeshCore-pakkeformatet (header, path, AES-128-ECB + 2-byte HMAC for gruppebeskeder). Test den mod din egen observer – især `path_len`-kodningen kan variere mellem firmwareversioner.

## Vilkår og privatliv

- [Servicevilkår](TERMS.md)
- [Privatlivspolitik](PRIVACY.md)
