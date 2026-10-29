# Security notes

- **No password handling.** NOVA never asks for, receives, or stores a
  Facebook password. You log in manually in the browser engine's own window
  (Termux Browser Pilot's Firefox, or the WebDroid app).
- **No cookie/token access.** NOVA does not read, copy, print, or store
  session cookies or access tokens — not in the database, not in logs, not
  in exports. Session persistence is the engine's own feature (TBP profile
  under `~/.tbp`, WebDroid's app-private WebView storage).
- **Logout / session deletion.** `nova session delete` (TBP) stops the
  daemon and deletes TBP's own profile + auto-cookie files under `~/.tbp`,
  only after you type DELETE. For WebDroid, log out inside the app or clear
  its app data.
- **No bypasses.** NOVA does not bypass CAPTCHA, MFA, checkpoints, or login
  walls. When Facebook asks for verification, NOVA pauses and tells you to
  resolve it manually in the browser, then resume. TBP's Cloudflare/stealth/
  spoofing features are deliberately **not used** by NOVA.
- **Polite collection.** Scroll waits are configurable (default 2.5 s) and
  the loop stops on limits; there is no rate-limit evasion.
- **Local data only.** Records live in `~/.nova/nova.db` inside Termux's
  private storage on your phone. Nothing is uploaded anywhere by NOVA.
- **What gets stored per record:** source page URL, post URL, object type/id,
  extraction method, timestamps, validation status, confidence. Never
  credentials or session material.
- **Use your own account**, and content you are allowed to access. You are
  responsible for complying with Facebook's Terms of Service.
