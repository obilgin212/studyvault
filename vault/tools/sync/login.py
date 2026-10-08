"""Sign-in for the class-sync collector and file downloads (first time, then about every 2 weeks when it expires).

Opens a *normal* Google Chrome window (not automated) using the collector's own profile. {{NAME}} signs in to the
school account by hand (the school's own sign-in page), checks that Classroom and Google Docs both load, then closes the
window. The collector and fetch.py reuse that saved session. No password is ever seen or stored by these scripts;
Chrome keeps the cookies in PROFILE_DIR.

  ~/miniconda3/envs/study/bin/python tools/sync/login.py
"""
import subprocess
import sys

from common import CHROME, PROFILE_DIR, STATE_FILE, load_json, save_json

PROFILE_DIR.mkdir(parents=True, exist_ok=True)
print("A separate Chrome window will open (its own profile, not your usual one), with two tabs.")
print("1) Sign in with your SCHOOL account only (one account keeps Drive links working).")
print("2) Check that BOTH tabs load: Google Classroom with your classes, and the Google Docs home page.")
print("   (Docs needs its own sign-in check; without it, Docs in assignments can't be downloaded.)")
print("3) Close that Chrome window (⌘Q while it's focused). The session is saved for about 2 weeks.\n")
proc = subprocess.run([CHROME, f"--user-data-dir={PROFILE_DIR}", "--no-first-run", "--no-default-browser-check",
                       "https://classroom.google.com/", "https://docs.google.com/document/u/0/"])
state = load_json(STATE_FILE, {})
if state.get("status", {}).get("error") == "needs login":
    state["status"] = {"ok": None, "when": None, "error": None, "note": "signed in again; next sync will confirm"}
    save_json(STATE_FILE, state)
sys.exit(proc.returncode)
