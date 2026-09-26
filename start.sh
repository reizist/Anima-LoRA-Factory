#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

APP_PORT=${APP_PORT:-8000}
export APP_PORT PYTHONUTF8=1

find_python() {
    for candidate in python3.12 python3.11 python3.10 python3; do
        if command -v "$candidate" >/dev/null 2>&1 && \
            "$candidate" -c 'import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 1)' 2>/dev/null; then
            command -v "$candidate"
            return 0
        fi
    done
    return 1
}

PYTHON_BIN=$(find_python || true)

echo "[Anima LoRA Factory] Initializing on $(uname -s)..."

if [ ! -x "$SCRIPT_DIR/venv/bin/python" ]; then
    echo "[INFO] Creating virtual environment venv..."
    if [ -n "$PYTHON_BIN" ]; then
        "$PYTHON_BIN" -m venv "$SCRIPT_DIR/venv" || VENV_FAILED=1
    elif command -v uv >/dev/null 2>&1; then
        echo "[INFO] A supported system Python was not found; uv will provision Python 3.12."
        uv venv --python 3.12 "$SCRIPT_DIR/venv" || VENV_FAILED=1
    else
        VENV_FAILED=1
    fi
    if [ "${VENV_FAILED:-0}" = "1" ]; then
        echo "[ERROR] Failed to create venv."
        echo "[HINT] Install Python 3.10-3.12 and its venv module, or install uv."
        echo "[HINT] Ubuntu: sudo apt install python3-venv python3-tk"
        exit 1
    fi
fi

VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"
"$VENV_PYTHON" "$SCRIPT_DIR/backend/setup_check.py"

URL="http://localhost:$APP_PORT"
echo "[Anima LoRA Factory] Starting backend server..."
echo "Access the GUI at $URL"

if [ "${NO_BROWSER:-0}" != "1" ]; then
    case "$(uname -s)" in
        Darwin)
            command -v open >/dev/null 2>&1 && (sleep 2; open "$URL") &
            ;;
        Linux)
            command -v xdg-open >/dev/null 2>&1 && (sleep 2; xdg-open "$URL" >/dev/null 2>&1) &
            ;;
    esac
fi

cd "$SCRIPT_DIR/backend"
exec "$VENV_PYTHON" main.py
