#!/usr/bin/env bash
# Ace - CSMJ Tool launcher for macOS / Linux.
# Double-click on macOS (may need: right-click -> Open the first time).
set -e
cd "$(dirname "$0")"

echo "=================================================="
echo "   Ace - CSMJ Tool"
echo "=================================================="
echo

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

# --- Build the app environment on first run --------------------------------
if [ ! -x ".venv/bin/streamlit" ]; then
    echo "Setting up the app (first run may take a couple of minutes)..."
    echo
    uv venv --python 3.12
    uv pip install -r requirements.txt
fi

echo
echo "Starting the app... your browser will open at http://localhost:8501"
echo "Keep this window open while you work. Close it to stop the app."
echo
./.venv/bin/streamlit run app.py
