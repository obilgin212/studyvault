"""Give every open assignment its materials, so "help me with <assignment>" works straight away.

  materials.py [--refresh] [--only "<title words>"]

For each open item in the To-Do tracker (todo.json) it opens the assignment's Classroom details page (read-only,
with the saved session), then writes a "## 📎 Materials" section into the assignment note (creating the note if
there isn't one):
  * Classroom link, teacher, points, due date, and the teacher's instructions word for word;
  * every attachment and link: Google Drive/Docs files (linked; fetched with fetch.py when {{NAME}} asks for help with
    that assignment), Google Forms (link only: they're for {{NAME}} to fill in), and public web pages, which are saved
    as Markdown in Courses/<course>/_sources/web/ so the tutor can read them offline;
  * textbook pages the instructions mention ("p.297 #1, 3…"), resolved against the course's textbook if it has one.
Items captured in the last 24 h are skipped unless --refresh. Needs a recent collector snapshot (for the links).
"""
import argparse
import glob
import hashlib
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

from collect import BOILER, NOISE, NeedsLogin, read
from common import CONFIG_FILE, KEEP_KEYCHAIN, PROFILE_DIR, SYNC_DIR, VAULT, load_json, log, profile_lock, save_json
from todo import load as load_todo, render, save as save_todo
from webtext import fetch_markdown
from work import clean, short_class

ITEM_RE = re.compile(r"classroom\.google\.com/(?:u/\d+/)?c/([\w-]+)/([a-z]{1,3})/([\w-]+)")
CACHE = SYNC_DIR / "materials.json"
MARKERS = {"assignment", "question", "quiz", "live_help", "help", "assignment_late"}
STOP = {"Class comments", "Your work", "Private comments", "Your answer", "Add class comment"}
TYPE_WORDS = {"PDF", "Google Docs", "Google Slides", "Google Sheets", "Google Forms", "Google Drawings", "Link",
              "YouTube video", "Image", "Video", "Word", "PowerPoint", "Excel", "Drive folder", "Folder"}
SKIP_HOSTS = re.compile(r"(classroom|accounts|support|policies|myaccount|www)\.google\.com/?(?!.*(document|presentation|spreadsheets|forms|file|drive))|gstatic|googleusercontent")
PAGE_RE = re.compile(r"\bp(?:p|g|age)?s?\.?\s*(\d{1,4})(?:\s*[-–]\s*(\d{1,4}))?(?:\s*#\s*([\d,\s–-]+))?", re.I)
MATERIALS_H = "## 📎 Materials"


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def parse_details(pg):
    """Classroom details page -> dict(title, teacher, points, due_text, instructions[], attachments[])."""
    raw = [clean(l) for l in pg["text"].split("\n") if clean(l)]
    title = re.sub(r"\s*-\s*Classroom\s*$", "", pg.get("title") or "").strip()
    t_i = next((i for i, l in enumerate(raw) if l == title), None)
    due_i = next((i for i, l in enumerate(raw) if (t_i is None or i > t_i) and (l.startswith("Due ") or l == "No due date")), None)
    head = raw[t_i:due_i] if t_i is not None else []
    teacher = next((head[i + 1] for i, l in enumerate(head[:-1]) if l == "More options"), None)
    points = next((l for l in head if re.fullmatch(r"\d+ points?", l)), None)
    if due_i is not None:
        start = due_i + 1
    else:                       # questions / no-due items: body starts after the header block
        start = next((t_i + i + 1 for i, l in enumerate(head) if re.fullmatch(r"\d+ points?", l) or l == "|"),
                     (t_i or 0) + 5)
    body = []
    for l in raw[start:]:
        if l in STOP:
            break
        body.append(l)
    links, seen = [], set()
    for a in pg["links"]:
        h = a["href"]
        if not h.startswith("http") or h in seen or SKIP_HOSTS.search(h) or ITEM_RE.search(h):
            continue
        if "google.com" in h and not re.search(r"(drive|docs|forms)\.google\.com", h):
            continue
        seen.add(h)
        name = clean((a["label"] or a["text"]).replace("Attachment: ", "").split("\n")[0])
        name = re.sub(r"^(PDF|Google \w+|Link|YouTube video|Image|Video):\s*", "", name)
        if name.lower().startswith("link to ") or not name:
            # link cards show the page title as a text line just before the URL
            i = next((k for k, l in enumerate(body) if l.rstrip("/") == h.rstrip("/")), None)
            name = body[i - 1] if i else h
        links.append({"name": name, "url": h})
    names = {norm(x["name"]) for x in links}
    instructions = [l for l in body if l not in TYPE_WORDS and norm(l) not in names and not l.startswith("http")
                    and not NOISE.match(l) and l not in ("•", "|") and l not in BOILER]
    return {"title": title, "teacher": teacher, "points": points,
            "due_text": raw[due_i] if due_i is not None else "No due date", "instructions": instructions,
            "attachments": links}


def kind_of(url):
    if "forms.gle" in url or "docs.google.com/forms" in url:
        return "form"
    if re.search(r"(drive|docs)\.google\.com", url):
        return "drive"
    if re.search(r"youtube\.com|youtu\.be", url):
        return "video"
    return "web"


def save_web(url, course_dir):
    title, text = fetch_markdown(url)
    if not text:
        return None
    slug = re.sub(r"[^\w-]+", "-", re.sub(r"^https?://", "", url)).strip("-")[:90]
    out = course_dir / "_sources" / "web" / f"{slug}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"---\nsource: {url}\ntitle: \"{title}\"\nsaved: {datetime.now():%Y-%m-%d}\n---\n{text}\n")
    return out


def textbook_refs(instructions, course_dir):
    refs = []
    tb = course_dir / "_sources" / "textbook.pdf"
    for l in instructions:
        for m in PAGE_RE.finditer(l):
            p1 = int(m.group(1))
            ref = {"text": m.group(0).strip(), "page": p1, "exercises": (m.group(3) or "").strip(" ,")}
            ref["available"] = tb.exists()
            refs.append(ref)
    return refs


def local_file_for(att, course_dir):
    """A file with the same name already downloaded into the course's _sources?"""
    name = att["name"]
    if not name or "." not in name:
        return None
    for f in (course_dir / "_sources").rglob("*"):
        if f.is_file() and f.name.lower() == name.lower():
            return f
    return None


def materials_md(d, url, course, course_dir, refs, due=None):
    lines = [MATERIALS_H, f"*Captured from Classroom {datetime.now():%a %-m/%-d %-I:%M %p}. "
             f"Tutor: this is everything attached to the assignment; use it directly (CLAUDE.md principle 5).*", ""]
    lines.append(f"- **Classroom:** [{d['title'] or 'open'}]({url})")
    due_txt = "No due date"
    if due:
        dt = datetime.fromisoformat(due if len(due) > 10 else due + " 00:00")
        due_txt = "Due " + dt.strftime("%a %b %-d") + (dt.strftime(", %-I:%M %p") if len(due) > 10 else "")
    meta = " · ".join(x for x in (d["teacher"], d["points"], due_txt) if x)
    if meta:
        lines.append(f"- **Details:** {meta}")
    lines.append("")
    if d["instructions"]:
        lines += ["**Instructions (from the teacher):**", ""] + [f"> {l}" for l in d["instructions"]] + [""]
    else:
        lines += ["*No written instructions: the attachments below are the assignment.*", ""]
    if d["attachments"]:
        lines += ["**Attachments and links:**", ""]
        for a in d["attachments"]:
            k = a["kind"]
            if k == "web" and a.get("local"):
                lines.append(f"- 🌐 [{a['name']}]({a['url']}): saved locally as [[{a['local']}|a copy the tutor can read]]")
            elif k == "drive" and a.get("local"):
                lines.append(f"- 📄 [{a['name']}]({a['url']}): downloaded: [[{a['local']}]]")
            elif k == "drive":
                lines.append(f"- 📄 [{a['name']}]({a['url']}): Google Drive file, fetched when you ask for help "
                             f"(`tools/sync/fetch.py`)")
            elif k == "form":
                lines.append(f"- 📝 [{a['name']}]({a['url']}): Google Form for you to fill in")
            elif k == "video":
                lines.append(f"- 🎬 [{a['name']}]({a['url']})")
            else:
                lines.append(f"- 🔗 [{a['name']}]({a['url']})")
        lines.append("")
    if refs:
        lines += ["**Textbook pages mentioned:**", ""]
        for r in refs:
            ex = f", exercises {r['exercises']}" if r["exercises"] else ""
            where = (f"in `{course_dir.relative_to(VAULT)}/_sources/textbook.pdf` (render with `tools/pdf.py`)"
                     if r["available"] else "**textbook not in the vault yet** (`/add-course`)")
            lines.append(f"- p.{r['page']}{ex}: {where}")
        lines.append("")
    return "\n".join(lines)


def upsert_note(course, course_dir, d, url, due, block):
    folder = course_dir / "Assignments"
    folder.mkdir(parents=True, exist_ok=True)
    note = None
    for f in folder.glob("*.md"):
        head = f.read_text()[:1000]
        m = re.search(r'^title:\s*"?(.+?)"?\s*$', head, re.M)
        if (m and norm(m.group(1)) == norm(d["title"])) or url in head:
            note = f
            break
    if note is None:
        short = re.sub(r'[\\/:*?"<>|#^\[\]]+', " ", d["title"])[:60].strip()
        note = folder / f"{(due or datetime.now().isoformat())[:10]} {short}.md"
        note.write_text(f'---\ncourse: {course}\ntitle: "{d["title"]}"\ndue: {due or ""}\n'
                        f'status: not started\nsource: "{url}"\n---\n# {d["title"]}\n\n{block}\n'
                        f"Start with `/homework` (or just tell the tutor \"help me with {d['title']}\").\n")
        return note, True
    text = note.read_text()
    if MATERIALS_H in text:
        a = text.index(MATERIALS_H)
        nxt = re.search(r"^## ", text[a + len(MATERIALS_H):], re.M)
        b = a + len(MATERIALS_H) + nxt.start() if nxt else len(text)
        text = text[:a] + block + "\n" + text[b:]
    else:
        m = re.search(r"^# .+$", text, re.M)       # right after the H1 title
        at = m.end() + 1 if m else len(text)
        text = text[:at] + "\n" + block + "\n" + text[at:]
    note.write_text(text)
    return note, False


def course_dir_for(course, cfg_courses):
    if course in cfg_courses:
        return VAULT / "Courses" / course
    safe = re.sub(r'[\\/:*?"<>|]+', "-", course).strip()
    return VAULT / "Courses" / "Other" / safe          # clubs and classes /sync doesn't watch in depth


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--only")
    a = ap.parse_args()
    cfg = load_json(CONFIG_FILE, {})
    cfg_courses = {c["course"] for c in cfg.get("classes", [])}
    db = load_todo()
    cache = load_json(CACHE, {})
    snaps = sorted(glob.glob(str(SYNC_DIR / "20*" / "pages.json")))
    if not snaps:
        sys.exit("no collector snapshot yet: run collect.py")
    pages = load_json(snaps[-1], {})
    urls = []
    for src in [pages.get("todo") or {}] + [e.get("classwork", {}) for e in pages.get("classes", {}).values()] \
            + [e.get("stream", {}) for e in pages.get("classes", {}).values()]:
        for l in src.get("links", []):
            m = ITEM_RE.search(l["href"])
            if m and m.group(2) != "sp":
                u = l["href"].split("?")[0].rstrip("/")
                u = u if u.endswith("/details") else u + "/details"
                if u not in urls:
                    urls.append(u)
    open_items = {i: it for i, it in db["items"].items() if it["status"] == "open"}
    if a.only:
        open_items = {i: it for i, it in open_items.items() if a.only.lower() in it["title"].lower()}
    by_title = {norm(it["title"]): i for i, it in open_items.items()}
    fresh = datetime.now() - timedelta(hours=24)
    def needed(u):
        c = cache.get(u)
        if c is None:
            return True                                  # never seen: open it to learn which item it is
        if c.get("id") not in open_items:
            return False                                 # belongs to something already done / not tracked
        return a.refresh or not c.get("done") or datetime.fromisoformat(c["at"]) < fresh
    need = [u for u in urls if needed(u)]
    done_log = []
    with profile_lock(), sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(str(PROFILE_DIR), channel="chrome", headless=True,
                                                    ignore_default_args=KEEP_KEYCHAIN)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            home = read(page, "https://classroom.google.com/h", 1)
            BOILER.update(l.strip() for l in home["text"].split("\n") if l.strip())
            for u in need:
                try:
                    pg = read(page, u, 1)
                except NeedsLogin:
                    sys.exit("session expired: run tools/sync/login.py")
                except Exception as e:
                    log(f"materials: couldn't open {u}: {str(e)[:120]}")
                    continue
                d = parse_details(pg)
                iid = by_title.get(norm(d["title"]))
                cache[u] = {"at": datetime.now().isoformat(timespec="minutes"), "title": d["title"], "id": iid}
                if not iid:
                    continue
                it = db["items"][iid]
                course = it.get("course") or "Other"
                cdir = course_dir_for(course, cfg_courses)
                for att in d["attachments"]:
                    att["kind"] = kind_of(att["url"])
                    if att["kind"] == "web":
                        try:
                            f = save_web(att["url"], cdir)
                            if f:
                                att["local"] = str(f.relative_to(VAULT).with_suffix(""))
                        except Exception as e:
                            log(f"materials: couldn't save {att['url']}: {str(e)[:100]}")
                    elif att["kind"] == "drive":
                        f = local_file_for(att, cdir)
                        if f:
                            att["local"] = str(f.relative_to(VAULT))
                refs = textbook_refs(d["instructions"], cdir)
                block = materials_md(d, u, course, cdir, refs, it.get("due"))
                note, created = upsert_note(course, cdir, d, u, it.get("due"), block)
                it["note"] = str(note.relative_to(VAULT).with_suffix(""))
                it["url"] = u
                cache[u]["done"] = True
                cache[u]["hash"] = hashlib.md5(block.encode()).hexdigest()
                done_log.append(f"{'＋ note' if created else '↻ note'} {course}: {d['title']} "
                                f"({len(d['attachments'])} attachment(s){', textbook refs' if refs else ''})")
        finally:
            ctx.close()
    save_json(CACHE, cache)
    save_todo(db)
    render(db)
    missing = [it["title"] for i, it in open_items.items() if not db["items"][i].get("note")]
    for l in done_log:
        print(l)
    if missing:
        print("no Classroom page found for:", "; ".join(missing))
    log(f"materials: {len(done_log)} note(s) updated")


if __name__ == "__main__":
    main()
