"""Find the school's sign-in (SSO) page from the sync profile's history, for config.json → signin_markers.

  ~/miniconda3/envs/study/bin/python tools/sync/detect_sso.py [--write]

Run right after login.py. Lists the non-Google sites the sign-in window visited (the school's single-sign-on page is
almost always one of them, e.g. sso.district.org or a district identity portal). With --write, adds the most likely
one to config.json. Reads only page addresses from the separate sync profile, never cookies or passwords.
"""
import json
import shutil
import sqlite3
import sys
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from common import CONFIG_FILE, PROFILE_DIR

GOOGLE = ("google.com", "gstatic.com", "googleusercontent.com", "youtube.com", "googleapis.com")
HINTS = ("sso", "idp", "saml", "auth", "login", "signin", "portal", "id.", "adfs", "okta", "clever", "classlink",
         "microsoftonline")


def hosts():
    hist = PROFILE_DIR / "Default" / "History"
    if not hist.exists():
        sys.exit("No history in the sync profile yet: run login.py and sign in first.")
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "History"
        shutil.copy2(hist, copy)                      # Chrome locks the live file
        rows = sqlite3.connect(copy).execute("SELECT url, visit_count FROM urls").fetchall()
    c = Counter()
    for url, n in rows:
        u = urlparse(url)
        h = u.hostname or ""
        if u.scheme in ("http", "https") and h and not any(h == g or h.endswith("." + g) for g in GOOGLE):
            c[h] += n or 1
    return c


def main():
    c = hosts()
    if not c:
        print("Only Google pages were visited: the school signs in through Google itself, so no marker is needed.")
        return
    ranked = sorted(c, key=lambda h: (-sum(k in h for k in HINTS), -c[h]))
    print("Non-Google sites the sign-in window visited (most likely sign-in page first):")
    for h in ranked[:8]:
        print(f"  {h}  ({c[h]} visits)")
    if "--write" in sys.argv:
        best = ranked[0]
        cfg = json.loads(CONFIG_FILE.read_text())
        markers = cfg.setdefault("signin_markers", [])
        if best not in markers:
            markers.append(best)
            CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
        print(f"config.json → signin_markers now: {markers}")


if __name__ == "__main__":
    main()
