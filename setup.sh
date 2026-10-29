#!/data/data/com.termux/files/usr/bin/bash
# NOVA M3 installer for Android Termux.
# - Verifies the Termux environment
# - Installs Termux Browser Pilot (primary engine) via its own installer
# - Creates the private NOVA workspace (~/.nova) and installs the `nova` command
# - Runs a self-test (unit tests + offline extraction) and prints start commands
set -e

echo "=== NOVA M3 installer ==="

# 1. Environment check -------------------------------------------------------
if [ -z "$PREFIX" ] && [ ! -d /data/data/com.termux ]; then
  echo "ERROR: This installer targets Termux on Android."
  echo "Install Termux (F-Droid / GitHub releases), then run this inside it."
  exit 1
fi
command -v python3 >/dev/null || { echo "ERROR: python3 missing. Run: pkg install python"; exit 1; }
command -v git >/dev/null || { echo "Installing git..."; pkg install -y git; }

NOVA_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$NOVA_DIR"

# 2. Browser engine: Termux Browser Pilot ------------------------------------
if command -v tbp >/dev/null 2>&1; then
  echo "[ok] Termux Browser Pilot already installed: $(tbp --version 2>/dev/null || echo present)"
else
  echo "[..] Installing Termux Browser Pilot (Firefox + Xvfb; this downloads packages)..."
  if [ ! -d "$HOME/termux-browser-pilot" ]; then
    git clone https://github.com/salviz/termux-browser-pilot.git "$HOME/termux-browser-pilot"
  fi
  bash "$HOME/termux-browser-pilot/setup.sh"
fi

# 3. Private workspace + config ----------------------------------------------
mkdir -p "$HOME/.nova/exports" "$HOME/.nova/logs"
chmod 700 "$HOME/.nova"
if [ ! -f "$HOME/.nova/config.json" ]; then
  cp "$NOVA_DIR/config.example.json" "$HOME/.nova/config.json"
fi
echo "[ok] NOVA workspace: $HOME/.nova (config, database, exports, logs)"

# 4. `nova` command ------------------------------------------------------------
cat > "$PREFIX/bin/nova" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python3 "$NOVA_DIR/nova.py" "\$@"
EOF
chmod +x "$PREFIX/bin/nova"
echo "[ok] Command installed: nova"

# 5. Self-test -------------------------------------------------------------------
echo "[..] Running self-test (unit tests + offline extraction)..."
python3 -m unittest discover -s "$NOVA_DIR/tests" 2>&1 | tail -3
TMP_HOME="$(mktemp -d)"
NOVA_HOME="$TMP_HOME" python3 "$NOVA_DIR/nova.py" extract \
  --file "$NOVA_DIR/tests/fixtures/feed_sample.html" --mode hybrid >/dev/null
COUNT="$(NOVA_HOME="$TMP_HOME" python3 -c "import sqlite3;print(sqlite3.connect('$TMP_HOME/nova.db').execute('select count(*) from records').fetchone()[0])")"
echo "[ok] Offline self-test stored $COUNT records (expected 7)"
rm -rf "$TMP_HOME"

cat <<'MSG'

=== NOVA M3 is installed ===
Start:
  nova browser open          # starts TBP Firefox on virtual display :99
  pkg install -y x11vnc      # one-time: makes that display visible
  x11vnc -display :99 -forever -shared -nopw &
  # -> Open a VNC viewer app (e.g. bVNC), connect to localhost:5900, and log
  #    into YOUR Facebook account manually in the Firefox window you see.
  #    NOVA never asks for your password.
  nova session status        # confirm LOGGED_IN
  nova extract --mode hybrid --url https://www.facebook.com/<page-or-profile>
  nova export --format txt   # links land in ~/.nova/exports/

Help:        nova --help        |        Diagnostics:  nova diagnose
Docs:        README.md in this folder (compatibility matrix, security, troubleshooting)
MSG
