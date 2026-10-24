#!/usr/bin/env bash
# Install or update MeshDisc as a systemd service (Debian/Ubuntu, e.g. a Proxmox LXC).
# Run as root:  bash install.sh
# Running it again pulls the latest version and restarts the service.
set -euo pipefail

REPO="${REPO:-https://github.com/Fywqdk/MeshDisc.git}"
DIR=/opt/meshdisc
SERVICE=meshdisc

[ "$(id -u)" -eq 0 ] || { echo "Run as root"; exit 1; }

apt-get update -q
apt-get install -y -q git python3 python3-venv

id "$SERVICE" >/dev/null 2>&1 || useradd --system --home-dir "$DIR" --shell /usr/sbin/nologin "$SERVICE"

if [ -d "$DIR/.git" ]; then
    runuser -u "$SERVICE" -- git -C "$DIR" pull --ff-only
else
    git clone "$REPO" "$DIR"
fi

python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install -q --upgrade pip
"$DIR/.venv/bin/pip" install -q -r "$DIR/requirements.txt"

[ -f "$DIR/.env" ] || cp "$DIR/.env.example" "$DIR/.env"
chown -R "$SERVICE:" "$DIR"
chmod 600 "$DIR/.env"

install -m 644 "$DIR/deploy/meshdisc.service" "/etc/systemd/system/$SERVICE.service"
systemctl daemon-reload
systemctl enable -q "$SERVICE"

if grep -q '^DISCORD_TOKEN=din-bot-token-her' "$DIR/.env"; then
    echo
    echo "Installed. Fill in $DIR/.env (token, channel IDs, MESH_HOST), then run:"
    echo "  systemctl start $SERVICE && journalctl -u $SERVICE -f"
else
    systemctl restart "$SERVICE"
    echo
    echo "MeshDisc (re)started. Follow the log with:  journalctl -u $SERVICE -f"
fi
