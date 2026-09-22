#!/usr/bin/env bash
# Launch the Setlist -> Spotify Playlist Generator.
# Uses the venv's Python directly, so it works regardless of the
# calling shell (bash, fish, etc.) without needing to `source activate`.

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -x "venv/bin/python" ]; then
    echo "venv not found. Set it up first:" >&2
    echo "  python -m venv venv" >&2
    echo "  venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi

URL="http://127.0.0.1:8888/"

venv/bin/python app.py &
pid=$!
trap 'kill "$pid" 2>/dev/null' EXIT

# Wait for the server to come up, then open it in the browser.
for _ in $(seq 1 50); do
    if curl --output /dev/null --silent --head --fail "$URL"; then
        if command -v xdg-open >/dev/null; then
            xdg-open "$URL" >/dev/null 2>&1 &
        else
            echo "Server is up: $URL"
        fi
        break
    fi
    sleep 0.2
done

wait "$pid"
