#!/usr/bin/env bash
set -e

echo "[RudyRecord] Installing..."

# Create venv
VENV="$HOME/.rudyrecord/venv"
mkdir -p "$HOME/.rudyrecord"
python3 -m venv "$VENV"
source "$VENV/bin/activate"

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install psutil numpy opencv-python mss

# Ensure ~/.local/bin exists
mkdir -p "$HOME/.local/bin"

# Copy main script
cp rudyrecord.py "$HOME/.local/bin/rudyrecord"
chmod +x "$HOME/.local/bin/rudyrecord"

# Add PATH to bashrc if missing
if ! grep -q "$HOME/.local/bin" "$HOME/.bashrc"; then
    echo 'export PATH=$HOME/.local/bin:$PATH' >> "$HOME/.bashrc"
fi

echo "[OK] RudyRecord installed."
echo "Restart terminal or run: source ~/.bashrc"
echo "Run: rudyrecord start | stop | status"
