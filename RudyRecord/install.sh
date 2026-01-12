#!/usr/bin/env bash
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$APP_DIR/rudyrecord.py"

BASE="$HOME/.rudyrecord"
VENV="$BASE/venv"
BIN="$HOME/.local/bin"
LAUNCHER="$BIN/rudyrecord"

mkdir -p "$BASE" "$BIN"

python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install mss opencv-python numpy psutil

cp "$APP" "$BASE/rudyrecord.py"
chmod +x "$BASE/rudyrecord.py"

cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/python" "$BASE/rudyrecord.py" "\$@"
EOF

chmod +x "$LAUNCHER"

if ! echo "$PATH" | grep -q "$BIN"; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
fi

echo "[OK] Installed"
echo "Restart terminal or run:"
echo "export PATH=\$HOME/.local/bin:\$PATH"

