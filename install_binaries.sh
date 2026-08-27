#!/usr/bin/env bash
# macOS / Linux setup. COLMAP has no official binaries for these platforms,
# so it comes from Homebrew / apt; Brush is downloaded from GitHub releases.
set -e
cd "$(dirname "$0")"

PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then
    echo "[ERROR] Python 3.9+ is required. Install it and re-run this script."
    exit 1
fi

if ! command -v colmap >/dev/null 2>&1; then
    echo "COLMAP is not installed."
    if [ "$(uname)" = "Darwin" ]; then
        echo "Installing with Homebrew..."
        command -v brew >/dev/null 2>&1 && brew install colmap || \
            echo "Install Homebrew first: https://brew.sh"
    else
        echo "Installing with apt (sudo password may be requested)..."
        sudo apt-get update && sudo apt-get install -y colmap || \
            echo "Install COLMAP with your distribution's package manager."
    fi
fi

"$PY" bootstrap.py --setup
