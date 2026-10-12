#!/usr/bin/env bash
set -Eeuo pipefail

BOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$BOT_DIR"

if ! command -v screen >/dev/null 2>&1; then
    echo "Errore: screen non è installato."
    exit 1
fi

if [[ ! -x "$BOT_DIR/venv/bin/python" ]]; then
    echo "Errore: non trovo l'ambiente virtuale in $BOT_DIR/venv."
    exit 1
fi

echo "Aggiorno il bot dal ramo master..."
git pull --ff-only origin master

echo "Aggiorno le dipendenze Python..."
"$BOT_DIR/venv/bin/python" -m pip install -r "$BOT_DIR/requirements.txt"

echo "Riavvio la sessione screen del bot..."
screen -S botdiscord -X quit 2>/dev/null || true
sleep 1
screen -dmS botdiscord bash -c "cd \"$BOT_DIR\" && exec \"$BOT_DIR/venv/bin/python\" \"$BOT_DIR/main.py\""
sleep 1

if ! screen -list | grep -Fq ".botdiscord"; then
    echo "Errore: screen non ha mantenuto attiva la sessione botdiscord."
    exit 1
fi

echo "Bot aggiornato e riavviato nella sessione screen botdiscord."
