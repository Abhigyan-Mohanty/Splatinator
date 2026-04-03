#!/bin/bash

# Splatinator Binary Installer (Linux/Mac)
echo "=============================================="
echo "  Splatinator Binary Installer"
echo "=============================================="
echo ""

# Get script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Check if python3 is installed
if ! command -v python3 &> /dev/null
then
    echo "[ERROR] python3 could not be found. Please install it first."
    exit 1
fi

echo "Please select your target operating system:"
echo "1) macOS (Apple Silicon)"
echo "2) Linux (x86_64)"
echo ""

read -p "Enter choice (1-2) [Default 1]: " choice
choice=${choice:-1}

if [ "$choice" == "1" ]; then
    TARGET_OS="macos"
    echo "You selected macOS."
    python3 download_binaries.py --os macos
elif [ "$choice" == "2" ]; then
    TARGET_OS="linux"
    echo "You selected Linux."
    python3 download_binaries.py --os linux
else
    echo "Invalid choice."
    exit 1
fi

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Installation failed."
    exit 1
fi

echo ""
echo "=============================================="
echo "  Installation successfully finished!"
echo "=============================================="
