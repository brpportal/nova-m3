#!/data/data/com.termux/files/usr/bin/bash
# NOVA M3 diagnostics wrapper.
NOVA_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$NOVA_DIR/nova.py" diagnose
echo
echo "Engine binary: $(command -v tbp || echo 'tbp NOT FOUND')"
tbp status 2>/dev/null || true
