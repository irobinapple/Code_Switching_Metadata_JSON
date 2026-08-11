#!/usr/bin/env bash
# Get Ace - CSMJ Tool — one-time downloader for macOS / Linux.
# Double-click on macOS. The first time, right-click it -> Open -> Open, so
# macOS allows a file that came from the internet to run.
cd "$(dirname "$0")"

echo "=================================================="
echo "   Get Ace - CSMJ Tool  (one-time download)"
echo "=================================================="
echo

APP_BRANCH=main
REPO=https://github.com/irobinapple/Code_Switching_Metadata_JSON.git
FOLDER=Code_Switching_Metadata_JSON

# --- Git is required for the auto-updating copy ----------------------------
# On macOS `git` exists as a stub that fails until the Developer Tools are
# installed, so check that it actually runs rather than merely being present.
if ! git --version >/dev/null 2>&1; then
    echo "Git is not installed yet."
    if [ "$(uname)" = "Darwin" ]; then
        echo
        echo "A macOS window will open offering to install the Developer"
        echo "Tools (this includes Git). Click Install and wait for it to"
        echo "finish - it can take a few minutes - then run this file again."
        xcode-select --install >/dev/null 2>&1 || true
    else
        echo "Install git first, e.g.:  sudo apt install git"
    fi
    echo
    read -r -p "Press Enter to close..."
    exit 1
fi

# --- Download --------------------------------------------------------------
if [ -d "$FOLDER/.git" ]; then
    echo "The tool is already downloaded here. Nothing to do."
else
    echo "Downloading the tool... a sign-in window may appear the first time."
    if ! git clone -b "$APP_BRANCH" "$REPO" "$FOLDER"; then
        echo
        echo "Download failed. Check your internet connection / access, then"
        echo "run this file again."
        echo
        read -r -p "Press Enter to close..."
        exit 1
    fi
fi

# macOS tags anything downloaded from the internet, which makes Gatekeeper
# block the launcher. Clearing the tag lets it open with a normal double-click.
if [ "$(uname)" = "Darwin" ]; then
    xattr -dr com.apple.quarantine "$FOLDER" >/dev/null 2>&1 || true
fi
chmod +x "$FOLDER/Ace-CSMJ.command" >/dev/null 2>&1 || true

echo
echo "Done!"
echo "Open the folder  $FOLDER  and double-click  Ace-CSMJ.command"
echo "to start the tool. Keep that window open while you work."
echo
read -r -p "Press Enter to close..."
