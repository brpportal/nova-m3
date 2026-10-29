#!/data/data/com.termux/files/usr/bin/bash
# NOVA M3 launcher. setup.sh installs a copy of this as $PREFIX/bin/nova
# with NOVA_DIR set to the cloned project directory.
NOVA_DIR="${NOVA_DIR:-$HOME/nova-m3}"
exec python3 "$NOVA_DIR/nova.py" "$@"
