"""Shared paths and helpers for the class-sync collector (Option B: Playwright + saved Chrome session).

Read-only by design: it only navigates to pages and reads them. It never clicks buttons, submits forms,
types credentials, or downloads files (downloads go through fetch.py, only after {{NAME}} approves them in /sync).
"""
import json
import subprocess
from datetime import datetime
from pathlib import Path

VAULT = Path(__file__).resolve().parents[2]          # the vault this tools/ folder belongs to
SYNC_DIR = VAULT / "Inbox" / "sync"                    # snapshots Claude reads in /sync
STATE_FILE = SYNC_DIR / "state.json"                   # what has been seen before
CONFIG_FILE = Path(__file__).resolve().parent / "config.json"
PROFILE_DIR = Path.home() / "Library/Application Support/StudyVaultSync/chrome-profile"   # login cookies live here
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
LOG_FILE = SYNC_DIR / "collector.log"
# Playwright normally starts Chrome with a stand-in keychain. Then Chrome can't decrypt the cookies saved by the
# real sign-in (macOS encrypts them with the Keychain), treats the session as gone, and deletes it.
# Always launch with the real Keychain.
KEEP_KEYCHAIN = ["--use-mock-keychain", "--password-store=basic"]


class profile_lock:
    """Only one tool may drive the sync Chrome profile at a time (Chrome refuses a second instance).
    Waits up to `wait` seconds for the other run to finish."""
    def __init__(self, wait=1800):
        self.wait = wait

    def __enter__(self):
        import fcntl
        import time
        PROFILE_DIR.parent.mkdir(parents=True, exist_ok=True)
        self.f = open(PROFILE_DIR.parent / "profile.lock", "w")
        t0 = time.time()
        while True:
            try:
                fcntl.flock(self.f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except BlockingIOError:
                if time.time() - t0 > self.wait:
                    raise RuntimeError("the sync browser profile is busy (another sync step is running)")
                time.sleep(5)

    def __exit__(self, *a):
        import fcntl
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False))


def log(msg):
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def notify(title, message):
    """macOS notification (no-op if it fails)."""
    esc = lambda s: s.replace("\\", "\\\\").replace('"', '\\"')
    subprocess.run(["osascript", "-e", f'display notification "{esc(message)}" with title "{esc(title)}"'],
                   capture_output=True)


# Where an expired school session lands: Google's own sign-in, or the school's single-sign-on page
# (config.json → signin_markers, e.g. a district portal's host name).
SIGNIN_MARKERS = ("accounts.google.com", "ServiceLogin")


def _school_markers():
    try:
        return tuple(json.loads(CONFIG_FILE.read_text()).get("signin_markers", []))
    except Exception:
        return ()


def is_signin(url_or_html):
    """True if this URL (or page HTML) is a sign-in page rather than the content we asked for."""
    text = (url_or_html or "")[:20000]
    return any(m in text for m in SIGNIN_MARKERS + _school_markers())


def mark_needs_login(where):
    """Record an expired session so /sync and the tutor tell {{NAME}} to run login.py; notify once a day."""
    from datetime import date, datetime
    state = load_json(STATE_FILE, {})
    state["status"] = {"ok": False, "when": datetime.now().isoformat(timespec="minutes"), "error": "needs login",
                       "where": where}
    today = date.today().isoformat()
    if state.get("login_notified") != today:
        notify("School sign-in expired", "Run tools/sync/login.py and sign in (about every 2 weeks)")
        state["login_notified"] = today
    save_json(STATE_FILE, state)
    log(f"session expired (seen by {where}): run tools/sync/login.py")
