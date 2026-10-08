"""Download one class file with the saved school session (when {{NAME}} asks for help with that assignment, or approves it in /sync).

  ~/miniconda3/envs/study/bin/python tools/sync/fetch.py <drive-or-docs-url> <dest-folder> [--name FILE]

Drive files (PDFs, images…): downloaded directly.
Google Docs / Slides / Sheets: the file is opened in a real page first (so Google applies the school session to
docs.google.com), then exported as PDF; if PDF export is refused, Docs fall back to plain text (.txt), Sheets to .csv.

Exit codes: 0 ok · 1 failed (message says why) · 3 the school sign-in expired → run tools/sync/login.py
(about every 2 weeks; the school sends you to its own sign-in page).
"""
import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

from common import KEEP_KEYCHAIN, PROFILE_DIR, is_signin, log, mark_needs_login, profile_lock

KINDS = {"document": ("pdf", "txt"), "presentation": ("pdf",), "spreadsheets": ("pdf", "csv")}


def parse(url):
    m = re.search(r"/d/([\w-]+)|[?&]id=([\w-]+)", url)
    if not m:
        return None, None
    fid = m.group(1) or m.group(2)
    kind = next((k for k in KINDS if f"docs.google.com/{k}" in url), "drive")
    return kind, fid


def export_url(kind, fid, fmt):
    if kind == "presentation":
        return f"https://docs.google.com/presentation/d/{fid}/export/{fmt}"
    return f"https://docs.google.com/{kind}/d/{fid}/export?format={fmt}"


def filename(resp, fallback):
    cd = resp.headers.get("content-disposition", "")
    m = re.search(r"filename\*=UTF-8''([^;]+)|filename=\"?([^\";]+)", cd)
    name = unquote(m.group(1) or m.group(2)) if m else fallback
    return re.sub(r'[\\/:*?"<>|]+', " ", name).strip()


def expired():
    mark_needs_login("fetch.py")
    print("Your school sign-in has expired (Google sent the request to the school sign-in page). "
             "Run: ~/miniconda3/envs/study/bin/python tools/sync/login.py, sign in, open Classroom and a Google Doc, "
             "close the window, then try again.", file=sys.stderr)
    sys.exit(3)


def ok_file(resp):
    ctype = resp.headers.get("content-type", "")
    return resp.status == 200 and "text/html" not in ctype


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("dest")
    ap.add_argument("--name")
    a = ap.parse_args()
    kind, fid = parse(a.url)
    if not fid:
        sys.exit(f"not a Drive/Docs file link: {a.url}")
    dest = Path(a.dest).expanduser()
    dest.mkdir(parents=True, exist_ok=True)
    out = None
    with profile_lock(), sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(str(PROFILE_DIR), channel="chrome", headless=True,
                                                    ignore_default_args=KEEP_KEYCHAIN)
        try:
            if kind == "drive":
                r = ctx.request.get(f"https://drive.google.com/uc?export=download&id={fid}", timeout=120000)
                if not ok_file(r):
                    if is_signin(r.url) or is_signin(r.text()[:20000]):
                        ctx.close()
                        expired()
                    sys.exit(f"download failed (HTTP {r.status}). Very large or view-only Drive files can't be "
                             "fetched this way: open the link and download it by hand, or drop it in Inbox/.")
                out = dest / (a.name or filename(r, "download.pdf"))
                out.write_bytes(r.body())
            else:
                page = ctx.new_page()
                page.goto(f"https://docs.google.com/{kind}/d/{fid}/edit", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2500)
                if is_signin(page.url):
                    ctx.close()
                    expired()
                title = re.sub(r"\s*-\s*Google (Docs|Slides|Sheets)\s*$", "", page.title()).strip() or fid
                tried = []
                for fmt in KINDS[kind]:
                    r = page.request.get(export_url(kind, fid, fmt), timeout=120000)
                    tried.append(f"{fmt}: HTTP {r.status}")
                    if ok_file(r):
                        base = a.name or filename(r, f"{title}.{fmt}")
                        if not base.lower().endswith("." + fmt):
                            base += "." + fmt
                        out = dest / base
                        out.write_bytes(r.body())
                        break
                if not out:
                    sys.exit(f"export refused ({', '.join(tried)}). The owner may have turned off download/copy for this "
                             "file. Ask {{NAME}} for a screenshot, or read it on screen.")
        finally:
            try:
                ctx.close()
            except Exception:
                pass
    log(f"fetched {out} ({out.stat().st_size / 1e6:.1f} MB)")
    print(out)


if __name__ == "__main__":
    main()
