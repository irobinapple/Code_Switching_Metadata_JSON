#!/usr/bin/env bash
# Ace - CSMJ Tool launcher for macOS / Linux.
# Double-click on macOS (may need: right-click -> Open the first time).
set -e
cd "$(dirname "$0")"

echo "=================================================="
echo "   Ace - CSMJ Tool"
echo "=================================================="
echo

# --- Auto-update if this is a Git-linked copy ------------------------------
NEED_SYNC=0
if [ -d ".git" ] && command -v git >/dev/null 2>&1; then
    echo "Checking for updates..."
    BEFORE=$(git rev-parse HEAD 2>/dev/null || echo none)
    git pull --quiet || true
    AFTER=$(git rev-parse HEAD 2>/dev/null || echo none)
    if [ "$BEFORE" != "$AFTER" ]; then
        echo "Updated to the latest version."
        NEED_SYNC=1
    fi
fi

# --- Make sure the uv runtime is available ---------------------------------
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
    echo "First-time setup: installing the uv runtime (one-time)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi
if ! command -v uv >/dev/null 2>&1; then
    echo
    echo "Could not install uv automatically."
    echo "Please install uv from https://docs.astral.sh/uv/ and try again."
    echo
    read -r -p "Press Enter to close..."
    exit 1
fi

# --- Skip Streamlit's first-run email prompt -------------------------------
mkdir -p "$HOME/.streamlit"
if [ ! -f "$HOME/.streamlit/credentials.toml" ]; then
    printf '[general]\nemail = ""\n' > "$HOME/.streamlit/credentials.toml"
fi

# --- Build the app environment; re-sync only after an update ---------------
if [ ! -x ".venv/bin/streamlit" ]; then
    echo "Setting up the app (first run may take a couple of minutes)..."
    echo
    uv venv --python 3.12
    NEED_SYNC=1
fi
if [ "$NEED_SYNC" = "1" ]; then
    echo "Installing / updating components..."
    uv pip install -r requirements.txt
fi

echo
echo "Starting the app... your browser will open at http://localhost:8501"
echo "Keep this window open while you work. Close it to stop the app."
echo
./.venv/bin/streamlit run app.py
