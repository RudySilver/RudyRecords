#!/usr/bin/env bash

# -------------------------
# RudyRecord Installer
# -------------------------

set -e

echo "Installing RudyRecord..."

# Create virtual environment
python3 -m venv ~/.rudyrecord/venv
source ~/.rudyrecord/venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install psutil numpy opencv-python mss

# Make executable in ~/.local/bin
mkdir -p ~/.local/bin
cp rudyrecord.py ~/.local/bin/rudyrecord
chmod +x ~/.local/bin/rudyrecord

echo "[OK] RudyRecord installed."
echo "Ensure ~/.local/bin is in your PATH:"
echo '  export PATH=$HOME/.local/bin:$PATH'
echo "Run using: rudyrecord start"
