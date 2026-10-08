"""Class-sync collector: reads Google Classroom (with the session saved by login.py) and public class sites,
diffs against the last run, and writes a snapshot for /sync to process.

  ~/miniconda3/envs/study/bin/python tools/sync/collect.py [--headed] [--dry-run]

Output: Inbox/sync/<timestamp>/changes.md (+ pages.json). Nothing is written when nothing changed.
Read-only: navigation and reading only. The only clicks are the To-do page's section toggles and "View all",
which just show more of the list. No forms, no downloads.
"""
import argparse
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

from common import (is_signin, CONFIG_FILE, KEEP_KEYCHAIN, profile_lock, PROFILE_DIR, STATE_FILE, SYNC_DIR, load_json, log, notify, save_json)

CLASSROOM = "https://classroom.google.com"
ITEM_RE = re.compile(r"classroom\.google\.com/(?:u/\d+/)?c/([\w-]+)/([a-z]{1,3})/([\w-]+)")
CLASS_RE = re.compile(r"classroom\.google\.com/(?:u/\d+/)?c/([\w-]+)/?$")
ITEM_KIND = {"a": "assignment", "m": "material", "p": "post", "sa": "question", "mc": "question"}
ATTACH_RE = re.compile(r"(drive|docs)\.google\.com|youtube\.com|youtu\.be|forms\.gle|forms\.google")
NOISE = re.compile(r"^(more_vert|add comment|class comments|add class comment|\d+ class comments?|"
                   r"announce something to your class|stream|classwork|people|grades|home|calendar|"
                   r"to-do|to review|enrolled|archived classes|settings|help|view all|see all|"
                   r"no class comments|view more|done|turned in|assigned|missing|edit|new announcement|"
                   r"skip to main content|main menu|classroom|resources|teaching|your work|add|add or create|"
                   r"mark as done|private comments|add comment to .*|more options|help and feedback|"
                   r"keyboard_arrow_\w+|expand|collapse|collapse all|collapse all sections|collapse topic|"
                   r"topic filter|all topics|assignment_ind|view your work|book|screen reader support enabled\.|"
                   r"all classes|no due date|this week|next week|later|earlier|pdf|google forms|image|link)$", re.I)
SKIP_KINDS = {"sp"}          # "View your work" pages: 404 for students


class NeedsLogin(Exception):
    pass


# ---------- page reading ----------

TODO_SECTION = re.compile(r"^(No due date|This week|Last week|Next week|Later|Earlier|Missing)\b")


def section_is_open(page, name):
    lines = [l.strip() for l in page.inner_text("body").split("\n") if l.strip()]
    for i, l in enumerate(lines):
        if l == name:
            return "keyboard_arrow_up" in lines[i + 1:i + 4]
    return False


def press(page, locator):
    """Activate a toggle with the keyboard: after "View all" lengthens the list, tooltips and the footer sit on top
    of the section buttons and swallow mouse clicks."""
    page.mouse.move(2, 2)
    locator.scroll_into_view_if_needed(timeout=3000)
    locator.focus(timeout=3000)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1200)


def read_todo(page, url, delay):
    """The To-do page is an accordion: opening one section ("No due date 4", "Next week 1", ...) closes the others.
    Open each section in turn (display-only toggles, plus "View all" inside a long section) and combine the text."""
    pg = read(page, url, delay)
    labels = [page.locator("button[aria-expanded][aria-label]").nth(i).get_attribute("aria-label")
              for i in range(page.locator("button[aria-expanded][aria-label]").count())]
    sections = [l for l in labels if l and TODO_SECTION.match(l)]
    chunks, complete = [pg["text"]], True
    for lab in sections:
        name = TODO_SECTION.match(lab).group(1)
        btn = page.locator(f'button[aria-label="{lab}"]')
        try:
            if not section_is_open(page, name):
                press(page, btn)
            if not section_is_open(page, name):
                complete = False
            chunks.append(page.inner_text("body"))
        except Exception:
            complete = False
            continue
        more = page.get_by_text("View all", exact=True)      # only the open section's link is visible
        for k in range(more.count()):
            try:
                if more.nth(k).is_visible():
                    more.nth(k).click(timeout=3000)
                    page.wait_for_timeout(1500)
                    page.mouse.move(2, 2)
                    chunks.append(page.inner_text("body"))
                    break
            except Exception:
                pass
    pg["text"] = "\n".join(chunks)
    pg["expanded"] = complete and bool(sections)
    return pg


POSTS_JS = """() => [...document.querySelectorAll('[data-stream-item-id]')].map(el => ({
    id: el.getAttribute('data-stream-item-id'),
    lines: el.innerText.split('\\n').map(s => s.trim()).filter(Boolean),
    links: [...el.querySelectorAll('a[href]')].map(a => ({url: a.href,
        name: (a.getAttribute('aria-label') || a.innerText || '').trim().split('\\n')[0].replace(/^Attachment: /, '')}))
        .filter(l => /^https?:/.test(l.url) && !/classroom\\.google\\.com\\/(u\\/\\d+\\/)?(c|w|h|a)\\//.test(l.url)
                     && !/accounts\\.google|support\\.google/.test(l.url))
}))"""


def stream_posts(page):
    """Each stream post on the current page: its id, text lines and links (for announcements.py)."""
    try:
        return [p for p in page.evaluate(POSTS_JS) if p["id"] and p["lines"]]
    except Exception:
        return []


def read(page, url, delay):
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    try:
        page.wait_for_load_state("networkidle", timeout=4000)   # Classroom never goes fully idle
    except PWTimeout:
        pass
    if is_signin(page.url):
        raise NeedsLogin(url)
    for _ in range(4):                      # Classroom lazy-loads older posts while scrolling
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(600)
    page.wait_for_timeout(int(delay * 1000))
    text = page.evaluate("() => (document.querySelector('main') || document.body).innerText")
    links = page.evaluate("""() => [...document.querySelectorAll('a[href]')].map(a => ({
        href: a.href, text: (a.innerText || '').trim().slice(0, 200), label: a.getAttribute('aria-label') || ''}))""")
    return {"url": url, "final_url": page.url, "title": page.title(), "text": text, "links": links}


BOILER = set()   # sidebar lines (class names, room numbers) taken from the home page each run


def lines_of(text):
    out = []
    for l in text.split("\n"):
        l = l.strip()
        if len(l) > 2 and not NOISE.match(l) and l not in BOILER:
            out.append(l)
    return out


def items_in(pg):
    """Classroom items (assignments, materials, posts) linked from a page: {key: {...}}."""
    found = {}
    for a in pg["links"]:
        m = ITEM_RE.search(a["href"])
        if not m:
            continue
        cid, kind, iid = m.groups()
        if kind in SKIP_KINDS:
            continue
        key = f"{cid}/{kind}/{iid}"
        name = (a["text"] or a["label"]).split("\n")[0].strip()
        if key not in found or (name and not found[key]["name"]):
            base = a["href"].split("?")[0].rstrip("/")
            found[key] = {"key": key, "kind": ITEM_KIND.get(kind, kind), "name": name,
                          "url": base if base.endswith("/details") else base + "/details"}
    return found


def attachments(pg):
    seen, out = set(), []
    for a in pg["links"]:
        if ATTACH_RE.search(a["href"]) and a["href"] not in seen:
            seen.add(a["href"])
            out.append({"name": (a["label"] or a["text"]).replace("Attachment: ", "").split("\n")[0][:150],
                        "url": a["href"]})
    return out


# ---------- public sites (no login) ----------

def public_changes(site, state):
    prev = state.setdefault("public", {}).setdefault(site["name"], {})
    with urllib.request.urlopen(site["sitemap"], timeout=30) as r:
        root = ET.fromstring(r.read())
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    changed = []
    for u in root.findall("s:url", ns):
        loc = u.findtext("s:loc", default="", namespaces=ns)
        mod = u.findtext("s:lastmod", default="", namespaces=ns)
        if not loc.startswith(site["prefix"]):
            continue
        if prev.get(loc) != mod:
            changed.append({"url": loc, "lastmod": mod, "new": loc not in prev})
        prev[loc] = mod
    return changed


# ---------- main ----------

def collect(headless, cfg, state):
    snap = {"when": datetime.now().isoformat(timespec="minutes"), "classes": {}, "college": {}, "todo": None}
    with profile_lock(), sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(str(PROFILE_DIR), channel="chrome", headless=headless, ignore_default_args=KEEP_KEYCHAIN,
                                                    viewport={"width": 1280, "height": 900})
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            delay = cfg.get("page_delay_seconds", 2)
            home = read(page, CLASSROOM + "/h", delay)
            texts = {}   # class id -> every text/label its links carry (the first one is often just the avatar letter)
            for a in home["links"]:
                m = CLASS_RE.search(a["href"].split("?")[0])
                if m:
                    for t in (a["text"], a["label"]):
                        texts.setdefault(m.group(1), []).extend(x.strip() for x in t.split("\n") if x.strip())
            classes = {cid: max(ts, key=len) if ts else cid for cid, ts in texts.items()}
            state["class_names"] = classes
            # everything on the home page is sidebar/class-card text that repeats on every other page
            BOILER.update(l.strip() for l in home["text"].split("\n") if l.strip())
            for spec in cfg["classes"]:
                cid = next((c for c, ts in texts.items() if any(spec["match"].lower() in t.lower() for t in ts)), None)
                if not cid:
                    log(f"class not found on Classroom home: {spec['match']!r}")
                    continue
                entry = {"course": spec["course"], "name": classes[cid], "id": cid}
                entry["stream"] = read(page, f"{CLASSROOM}/c/{cid}", delay)
                entry["posts"] = stream_posts(page)
                entry["classwork"] = read(page, f"{CLASSROOM}/w/{cid}/t/all", delay)
                cw_lines = entry["classwork"]["text"].split("\n")
                if any(l.strip() == "Assignment" for l in cw_lines) and not any(l.strip().startswith("Completed") for l in cw_lines):
                    # turn-in statuses load separately; a page read too early shows every item as not completed
                    page.wait_for_timeout(6000)
                    entry["classwork"] = read(page, f"{CLASSROOM}/w/{cid}/t/all", delay)
                    cw_lines = entry["classwork"]["text"].split("\n")
                    entry["status_loaded"] = any(l.strip().startswith("Completed") for l in cw_lines)
                    if not entry["status_loaded"]:
                        log(f"{spec['course']}: Classwork turn-in statuses didn't load; not using them this run")
                snap["classes"][spec["course"]] = entry
            # college-only sources (e.g. the senior-class classroom): stream + classwork, read for college_posts.py
            for spec in cfg.get("college_classes", []):
                cid = next((c for c, ts in texts.items() if any(spec["match"].lower() in t.lower() for t in ts)), None)
                if not cid:
                    log(f"college class not found on Classroom home: {spec['match']!r}")
                    continue
                entry = {"course": spec["course"], "name": classes[cid], "id": cid, "kind": "college"}
                entry["stream"] = read(page, f"{CLASSROOM}/c/{cid}", delay)
                entry["posts"] = stream_posts(page)
                entry["classwork"] = read(page, f"{CLASSROOM}/w/{cid}/t/all", delay)
                snap["college"][spec["course"]] = entry
            if cfg.get("include_todo", True):
                snap["todo"] = read_todo(page, CLASSROOM + "/a/not-turned-in/all", delay)
                snap["todo_expanded"] = bool(snap["todo"].get("expanded"))
                # Classroom keeps past-due, not-turned-in work on a separate "Missing" list
                snap["missing"] = read_todo(page, CLASSROOM + "/a/missing/all", delay)
                snap["missing_expanded"] = bool(snap["missing"].get("expanded")) or "No work missing" in snap["missing"]["text"]

            # details of items never seen before
            seen = state.setdefault("seen_items", {})
            budget = cfg.get("max_new_details_per_run", 25)
            for course, entry in [*snap["classes"].items(), *snap["college"].items()]:
                items = {**items_in(entry["stream"]), **items_in(entry["classwork"])}
                entry["items"] = items
                for key, it in items.items():
                    if key in seen:
                        continue
                    it["new"] = True
                    if cfg.get("open_new_item_details", True) and budget > 0:
                        budget -= 1
                        try:
                            d = read(page, it["url"], delay)
                            it["details_text"] = d["text"][:6000]
                            it["attachments"] = attachments(d)
                        except NeedsLogin:
                            raise
                        except Exception as e:      # one bad page shouldn't stop the run
                            it["error"] = str(e)[:200]
        finally:
            ctx.close()
    return snap


def diff_and_write(snap, public, state, first_run, dry):
    prev_lines = state.setdefault("page_lines", {})
    seen = state.setdefault("seen_items", {})
    out = [f"# Class sync {snap['when'].replace('T', ' ')}", ""]
    if first_run:
        out += ["> First run: this is a **baseline** of everything currently posted, not just new things.", ""]
    n_new = 0
    touched = []

    def new_lines(key, pg):
        cur = lines_of(pg["text"])
        old = set(prev_lines.get(key, []))
        prev_lines[key] = cur[:1500]
        return [l for l in cur if l not in old]

    for course, e in [*snap["classes"].items(), *snap.get("college", {}).items()]:
        sec = []
        new_items = [it for it in e.get("items", {}).values() if it.get("new")]
        if new_items:
            sec.append("### New items")
            for it in new_items:
                sec.append(f"- **{it['kind']}**: {it['name'] or '(untitled)'}: {it['url']}")
                if it.get("details_text"):
                    body = " / ".join(lines_of(it["details_text"]))[:1200]
                    sec.append(f"  - details: {body}")
                for at in it.get("attachments", []):
                    sec.append(f"  - 📎 {at['name']}: {at['url']}")
                seen[it["key"]] = {"name": it["name"], "course": course, "first_seen": snap["when"]}
            n_new += len(new_items)
        for part in ("stream", "classwork"):
            nl = new_lines(f"{course}:{part}", e[part])
            if nl and not first_run:
                sec.append(f"### New text on {part}")
                sec += [f"> {l}" for l in nl[:80]]
        if sec:
            touched.append(course)
            out += [f"## {course} ({e['name']})", *sec, ""]
    if snap.get("missing"):
        nl = new_lines("missing", snap["missing"])
        if nl:
            out += ["## Missing on Classroom (past due, not turned in)", *[f"> {l}" for l in nl[:60]], ""]
            touched.append("missing")
    if snap.get("todo"):
        nl = new_lines("todo", snap["todo"])
        if nl:
            out += ["## To-do (all classes: not turned in)", *[f"> {l}" for l in nl[:100]], ""]
    if public:
        out.append("## Public class sites")
        for site, pages in public.items():
            for p in pages[:60]:
                out.append(f"- {site}: {'NEW' if p['new'] else 'updated'} {p['url']} ({p['lastmod'][:10]})")
        out.append("")

    changed = bool(touched or n_new or any(public.values()) or (snap.get("todo") and "## To-do" in "\n".join(out)))
    if dry:
        print("\n".join(out))
        return None, n_new, touched
    save_json(STATE_FILE, state)
    if not changed:
        return None, 0, []
    d = SYNC_DIR / datetime.now().strftime("%Y-%m-%d_%H%M")
    d.mkdir(parents=True, exist_ok=True)
    (d / "changes.md").write_text("\n".join(out) + "\n")
    save_json(d / "pages.json", snap)
    save_json(d / "status.json", {"processed": False, "first_run": first_run})
    return d, n_new, touched


def list_classes(cfg):
    """Read only the Classroom home page and print class names, for setting up config.json."""
    with profile_lock(), sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(str(PROFILE_DIR), channel="chrome", headless=True,
                                                    ignore_default_args=KEEP_KEYCHAIN, viewport={"width": 1280, "height": 900})
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            try:
                home = read(page, CLASSROOM + "/h", cfg.get("page_delay_seconds", 2))
            except NeedsLogin:
                print("Not signed in: run login.py first.")
                return 3
            names = {}
            for a in home["links"]:
                m = CLASS_RE.search(a["href"].split("?")[0])
                if m:
                    for t in (a["text"], a["label"]):
                        names.setdefault(m.group(1), []).extend(x.strip() for x in t.split("\n") if x.strip())
            for cid, ts in names.items():
                print(max(ts, key=len) if ts else cid)
        finally:
            ctx.close()
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    ap.add_argument("--dry-run", action="store_true", help="print changes, don't save state or a snapshot")
    ap.add_argument("--list-classes", action="store_true",
                    help="print every class name on the Classroom home page (to fill in config.json), then exit")
    ap.add_argument("--daily", action="store_true",
                    help="scheduled mode: do nothing if today's run already succeeded (launchd tries hourly)")
    a = ap.parse_args()
    cfg = load_json(CONFIG_FILE, {})
    if a.list_classes:
        return list_classes(cfg)
    state = load_json(STATE_FILE, {})
    first_run = not state.get("seen_items")
    today = datetime.now().date().isoformat()
    if a.daily:
        st = state.get("status", {})
        if st.get("ok") and str(st.get("when", "")).startswith(today):
            return 0                                   # already done today: exit quietly
        log("daily run starting")
    if not PROFILE_DIR.exists():
        log("no saved session: run tools/sync/login.py first")
        notify("Class sync", "Sign in first: run tools/sync/login.py")
        return 2
    headless = cfg.get("headless", True) and not a.headed
    try:
        try:
            snap = collect(headless, cfg, state)
        except NeedsLogin:
            if not headless:
                raise
            log("headless run was sent to a sign-in page; retrying with a visible window once")
            snap = collect(False, cfg, state)
    except NeedsLogin:
        state["status"] = {"ok": False, "when": datetime.now().isoformat(timespec="minutes"), "error": "needs login"}
        save_json(STATE_FILE, state)
        log("session expired: run tools/sync/login.py")
        if state.get("login_notified") != today:
            notify("Class sync", "Your school sign-in expired. Run tools/sync/login.py")
            state["login_notified"] = today
            save_json(STATE_FILE, state)
        return 3
    except Exception as e:
        msg = str(e).splitlines()[0][:200]
        if "ProcessSingleton" in msg or "profile" in msg.lower() and "in use" in msg.lower():
            msg = "the sync Chrome profile is open in another window; close it and retry"
        state["status"] = {"ok": False, "when": datetime.now().isoformat(timespec="minutes"), "error": msg}
        save_json(STATE_FILE, state)
        log(f"collector failed: {msg}")
        if state.get("fail_notified") != today:
            notify("Class sync failed", msg + " (will retry next hour)")
            state["fail_notified"] = today
            save_json(STATE_FILE, state)
        return 1

    public = {}
    for site in cfg.get("public_sites", []):
        try:
            ch = public_changes(site, state)
            public[site["name"]] = [] if first_run else ch   # first run just records the baseline
        except Exception as e:
            log(f"public site {site['name']} failed: {e}")
    d, n_new, touched = diff_and_write(snap, public, state, first_run, a.dry_run)
    state["status"] = {"ok": True, "when": snap["when"], "snapshot": str(d) if d else None}
    if not a.dry_run:
        save_json(STATE_FILE, state)
    if d and cfg.get("auto_todo_and_materials", True):
        import subprocess
        py = sys.executable
        here = str(CONFIG_FILE.parent)
        steps = [["todo.py", "from-snapshot", str(d)], ["announcements.py", "--snapshot", str(d)],
                 ["college_posts.py", "--snapshot", str(d)], ["../college/college.py", "tracker"], ["../skilltree.py", "--all"], ["materials.py"]]
        last_index = state.get("classindex_at")
        if not last_index or datetime.now() - datetime.fromisoformat(last_index) > timedelta(hours=20):
            steps.append(["classindex.py"])
            state["classindex_at"] = datetime.now().isoformat(timespec="minutes")
            save_json(STATE_FILE, state)
        for args in steps:
            r = subprocess.run([py, *args], cwd=here, capture_output=True, text=True, timeout=900)
            log(f"{args[0]}: " + (r.stdout.strip().splitlines() or ["ok"])[-1][:160])
    if d:
        what = f"{n_new} new item(s)" + (f" in {', '.join(touched)}" if touched else "")
        log(f"changes → {d}")
        notify("Class sync", ("Baseline saved. " if first_run else "") + f"{what}. Run /sync in Claude.")
    else:
        log("no changes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
