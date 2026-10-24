# Opsætning og test i praksis

Målet er at få kæden **node → bot → Discord** til at virke. Hvert led testes for sig, så det er nemt at se, hvor det går galt.

Standard er **TCP direkte til en companion-node** (fx meshcomod på en Heltec V4). Noden sender en *RX log*-ramme for hver pakke, den hører, og botten dekrypterer selv kanalbeskederne. Der er ingen broker. Telefon-appen kan være forbundet samtidig, og botten rører ikke nodens beskedkø.

```
[Heltec V4 / meshcomod] --TCP :5000--> [bot] --> [Discord-kanal]
          ^
          +-- telefon-app (BLE/TCP) samtidig
```

Har du i stedet en observer, der publicerer MQTT, så se [MQTT-varianten](#mqtt-variant-observer--broker) nederst.

## 1. Gør noden klar

1. Forbind noden til dit Wi-Fi fra meshcomod-appen/-klienten.
2. Find nodens IP (i appen, på displayet eller i routerens DHCP-liste). Giv den gerne en fast IP/DHCP-reservation.
3. TCP-companion-serveren lytter på port **5000**. Tjek fra maskinen, der skal køre botten:

```bash
nc -vz 192.168.1.60 5000      # skal svare "succeeded" / "open"
```

## 2. Se hvad noden hører (uden Discord)

Kræver Python 3.11+:

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Sæt i `.env`: `MESH_SOURCE=tcp` og `MESH_HOST=<nodens IP>`. Kør så:

```bash
python -m tools.probe --all
```

Eksempel på output:

```
Lytter på MeshCore-node 192.168.1.60:5000 (TCP) … (Ctrl+C for stop)

── meshcore/TCP/Heltec V4/packets
   felter: RSSI, SNR, origin, raw
   pakke: GRP_TXT / FLOOD, path=['42'], 35 B payload
   🔓 #Public <Morten> Hej fra testen
   → Discord: Morten  ·  #Public: Hej fra testen
```

Hvad du skal kigge efter:

- **Ingen linjer efter "Lytter på"**: noden har ikke hørt noget endnu, eller den sender ikke RX log. Send en besked i Public fra en anden node.
- **`kunne ikke parse raw`**: formatet afviger fra det forventede. Send gerne et par linjer fra `samples.jsonl`, så kan parseren tilpasses.
- **`🔒 ukendt kanal`**: tilføj kanalens nøgle i `CHANNEL_KEYS`.

Bemærk: noden hører ikke sine egne udsendte beskeder i luften. Beskeder, du skriver fra telefonen forbundet til *samme* node, dukker kun op, hvis en repeater sender dem tilbage.

Alle beskeder gemmes i `samples.jsonl`. De er gode at have til test senere.

## 3. Opret Discord-botten

1. Gå til <https://discord.com/developers/applications> → **New Application** → giv den et navn.
2. **Bot** → **Reset Token** → kopiér tokenet til `DISCORD_TOKEN` i `.env`. Del det aldrig.
   Ingen *Privileged Gateway Intents* er nødvendige.
3. Slå **Developer Mode** til i Discord (Indstillinger → Avanceret). Højreklik kanalen → **Copy Channel ID** → `DISCORD_CHANNEL_ID`.
4. Kør tjekket, som også udskriver det korrekte invite-link:

```bash
python -m tools.discord_check --no-send
```

5. Åbn invite-linket, vælg din server, og godkend. Linket giver *View Channel*, *Send Messages* og *Embed Links* plus slash-kommandoer.
6. Kør tjekket igen uden `--no-send`. Der skal nu dukke en grøn testbesked op i kanalen:

```
✓ Logget ind som MeshBot#1234
✓ Kanal: #meshcore på Lan Team Nord
✓ Rettigheder OK (view_channel, send_messages, embed_links)
✓ Testbesked sendt: https://discord.com/channels/...
```

## 4. Kør det hele

```bash
docker compose up -d --build        # kun botten (TCP)
docker compose logs -f bot
```

eller uden Docker: `python -m meshbot`.

Skriv en besked i Public-kanalen fra en MeshCore-app. Den skal dukke op i Discord inden for et par sekunder.
`/mesh status` i Discord viser kilde, og hvor mange beskeder botten har modtaget, postet og frasorteret.

Mister noden Wi-Fi, forbinder botten selv igen (backoff op til 60 s). Botten sender også en keepalive hvert minut, så en død forbindelse opdages.

## MQTT-variant (observer + broker)

Bruges kun, hvis du har en node med observer-firmware, der selv publicerer MQTT. Sæt `MESH_SOURCE=mqtt` i `.env`, og start brokeren med profilen `mqtt`:

### Start MQTT-brokeren

Kræver Docker (Docker Desktop på Windows, `docker.io` + `docker-compose-plugin` på Pi/Linux).

```bash
cp .env.example .env

# Opret de to MQTT-brugere (vælg selv nogle stærke kodeord)
docker compose --profile mqtt run --rm --no-deps mosquitto sh -c '
  mosquitto_passwd -c -b /mosquitto/config/passwd observer  OBSERVER_KODE &&
  mosquitto_passwd    -b /mosquitto/config/passwd discordbot BOT_KODE &&
  chown mosquitto: /mosquitto/config/passwd && chmod 0700 /mosquitto/config/passwd'

docker compose --profile mqtt up -d mosquitto
docker compose logs mosquitto     # skal vise "Opening ipv4 listen socket on port 1883"
```

`mosquitto/config/acl` sørger for, at `observer` kun kan **skrive** til `meshcore/#`, og `discordbot` kun kan **læse**.
Brokeren afviser forbindelser uden gyldigt login.

> På Windows: tillad port 1883 i Windows Defender Firewall, så noden kan nå PC'en på LAN'et.

### Peg din observer mod brokeren

Sæt følgende i din nodes MQTT-bridge (fx meshcoretomqtt eller tilsvarende):

| Indstilling | Værdi |
|---|---|
| Server / host | IP på maskinen med Docker (fx `192.168.1.50`) |
| Port | `1883` |
| Brugernavn / kodeord | `observer` / `OBSERVER_KODE` |
| TLS | fra (på LAN) |
| Topic-præfiks | `meshcore` (giver `meshcore/<IATA>/<pubkey>/packets`) |

### Test uden rigtig observer

Sæt `MQTT_HOST=<broker-IP>`, `MQTT_USERNAME=discordbot`, `MQTT_PASSWORD=BOT_KODE` i `.env`, kør `python -m tools.probe --all`, og simulér en besked i en anden terminal:

```bash
python -m tools.send_test_packet "Hej fra testen" --sender Morten --user observer --password OBSERVER_KODE
```

Kør det hele med `docker compose --profile mqtt up -d --build`.

## Fejlsøgning

| Symptom | Årsag |
|---|---|
| `TCP-fejl … Connection refused` | Forkert IP/port, eller TCP er slået fra på noden |
| `TCP-fejl … timed out` | Noden er ikke på nettet, eller en firewall blokerer port 5000 |
| `MESH_HOST … skal være sat` | Udfyld `MESH_HOST` i `.env` |
| Forbinder, men intet modtages | Noden har ikke hørt pakker endnu, eller firmwaren sender ikke RX log til TCP-klienter |
| `Connection Refused: not authorised` | Forkert brugernavn/kodeord, eller `passwd` er ikke oprettet |
| Mosquitto: `Unable to open pwfile` | `passwd` ejes ikke af mosquitto. Kør `chown`-linjen fra trin 1 igen |
| Noden forbinder, men probe ser intet | Topic starter ikke med `meshcore/`, eller ACL blokerer. Tjek `docker compose logs mosquitto` |
| Publish "lykkes", men intet modtages | Mosquitto dropper beskeder, ACL ikke tillader, uden at give fejl (MQTT 3.1.1) |
| `Kan ikke se kanal` | Botten er ikke inviteret, eller mangler adgang til netop den kanal |
| Slash-kommandoer vises ikke | Det kan tage et øjeblik efter første start. Genstart Discord-klienten |
