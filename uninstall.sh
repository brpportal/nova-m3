#!/data/data/com.termux/files/usr/bin/bash
# NOVA M3 uninstaller. Removes the `nova` command. Your data (~/.nova) and the
# browser engine (Termux Browser Pilot) are removed ONLY if you confirm.
set -e
rm -f "$PREFIX/bin/nova"
echo "Removed: nova command"

read -r -p "Delete NOVA data (~/.nova: database + exports)? [y/N] " ans
if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
  rm -rf "$HOME/.nova"
  echo "Removed: ~/.nova"
fi

read -r -p "Also log out of Facebook in the browser engine (deletes TBP session under ~/.tbp)? [y/N] " ans2
if [ "$ans2" = "y" ] || [ "$ans2" = "Y" ]; then
  tbp stop 2>/dev/null || true
  rm -rf "$HOME/.tbp/firefox_profile" "$HOME/.tbp/auto_cookies.json"
  echo "Removed: TBP Firefox profile + auto cookies (you are logged out)"
fi
echo "Done. The cloned folders (nova-m3, termux-browser-pilot) were left in place; delete them manually if wanted."
