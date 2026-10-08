"""Per-class context for the tutor: every Classwork item, plus the syllabus and schedule as readable text.

  classindex.py [--course "AP Physics C"] [--refresh]

For each watched class (config.json) it writes, inside Courses/<course>/:
  * Class Materials.md: every Classwork item (materials, assignments, questions), grouped by Classroom topic, with
    posted/due info, the teacher's description, and every attachment (name + link). The tutor searches it to find
    things like "Chapter 6 guided notes" and fetches the file on demand.
  * Syllabus & Schedule.md: the text of the class's syllabus / schedule / calendar / course-at-a-glance documents,
    downloaded and converted (Docs → text, Sheets → table, PDFs → text), with links to the originals.
Read-only on Classroom: the only clicks are "View more" (shows older items). Item pages are cached in
Inbox/sync/classindex.json and only re-opened when Classroom shows them as new or edited, or with --refresh.
"""
import argparse
import base64
import csv
import io
import re
from datetime import datetime
from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright

from collect import BOILER, NeedsLogin, read, stream_posts
from common import CONFIG_FILE, KEEP_KEYCHAIN, PROFILE_DIR, SYNC_DIR, VAULT, load_json, log, profile_lock, save_json
from materials import kind_of, parse_details

CLASSROOM = "https://classroom.google.com"
CACHE = SYNC_DIR / "classindex.json"
KIND_PATH = {"Material": "m", "Assignment": "a", "Completed Assignment": "a", "Question": "sa",
             "Completed Question": "sa", "Quiz assignment": "a", "Completed Quiz assignment": "a"}
SYLLABUS_RE = re.compile(r"syllab|schedule|calendar|course at a glance|pacing|course outline|unit plan|"
                         r"expectations|course overview|class policies", re.I)


SUBMISSION_RE = re.compile(r"\(\w{3} \d{1,2}, \d{4} at \d{1,2}:\d{2}")   # a student's own turned-in file
AUTO_POST = re.compile(r'^(Assignment|Material|Question|Quiz assignment):\s*"|posted a new (assignment|material|question)', re.I)


def stream_entries(page, cid):
    """Teacher posts on the class stream (not the automatic 'posted a new assignment' items), with links."""
    from announcements import post_body, post_date
    from datetime import date as _date
    page.goto(f"{CLASSROOM}/c/{cid}", wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(3500)
    for _ in range(10):                      # older posts load as you scroll
        page.mouse.wheel(0, 6000)
        page.wait_for_timeout(700)
    out = []
    for p in stream_posts(page):
        lines = [l for l in p["lines"] if l.strip()]
        if not lines or AUTO_POST.search(" ".join(lines[:3])):
            continue
        d = post_date(lines, _date.today())
        body = post_body(lines)
        if not body or (not d and len(body) <= 2):      # empty, or a link-preview card inside another post
            continue
        links = []
        for l in p["links"]:
            l["name"] = re.sub(r"^(PDF|Google \w+|Link|YouTube video|Image|Video):\s*", "", l["name"] or "").strip()
            if not SUBMISSION_RE.search(l["name"]) and l["url"] not in {x["url"] for x in links}:
                links.append(l)
        out.append({"id": p["id"], "date": d.isoformat() if d else "", "body": body, "links": links})
    return out


def b64(n):
    return base64.b64encode(str(n).encode()).decode()


def classwork_entries(page, cid):
    """Every item on the Classwork page (after 'View more'), with its topic."""
    page.goto(f"{CLASSROOM}/w/{cid}/t/all", wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(3500)
    for _ in range(12):                      # "View more" reveals older items in a topic (display only)
        more = page.get_by_text("View more", exact=True)
        vis = [k for k in range(more.count()) if more.nth(k).is_visible()]
        if not vis:
            break
        try:
            more.nth(vis[0]).click(timeout=3000)
            page.wait_for_timeout(1200)
        except Exception:
            break
    return page.evaluate("""() => [...document.querySelectorAll('li[data-stream-item-id]')].map(li => {
        const sec = li.closest('[data-topic-id], section, [role=region]') ;
        let topic = '';
        let el = li.parentElement;
        for (let k = 0; k < 8 && el && !topic; k++) {
            const h = el.querySelector(':scope > div h2, :scope > h2, :scope > div [role=heading]');
            if (h) topic = h.innerText.trim();
            el = el.parentElement;
        }
        return {id: li.getAttribute('data-stream-item-id'), topic,
                lines: li.innerText.split('\\n').map(s => s.trim()).filter(Boolean).slice(0, 6)};
    })""")


def entry_fields(e):
    L = e["lines"]
    kind = L[0] if L else ""
    title = next((l for l in L[1:] if l.lower() not in ("book", "assignment", "help", "live_help", "quiz")), "")
    when = next((l for l in L if re.match(r"(Posted|Edited|Due)\b", l)), "")
    return kind, title, when


def doc_text(ctx, url):
    """Download a Google Doc/Sheet/Slides/Drive file and return (text, filename)."""
    m = re.search(r"/d/([\w-]+)|[?&]id=([\w-]+)", url)
    if not m:
        return None, None
    fid = m.group(1) or m.group(2)
    if "docs.google.com/document" in url:
        r = ctx.request.get(f"https://docs.google.com/document/d/{fid}/export?format=txt", timeout=120000)
        return (r.text() if r.ok else None), None
    if "docs.google.com/spreadsheets" in url:
        r = ctx.request.get(f"https://docs.google.com/spreadsheets/d/{fid}/export?format=csv", timeout=120000)
        if not r.ok:
            return None, None
        rows = list(csv.reader(io.StringIO(r.text())))
        rows = [r_ for r_ in rows if any(c.strip() for c in r_)]
        if not rows:
            return "", None
        w = max(len(r_) for r_ in rows)
        rows = [r_ + [""] * (w - len(r_)) for r_ in rows]
        md = ["| " + " | ".join(c.replace("|", "/").replace("\n", " ") for c in rows[0]) + " |",
              "|" + "---|" * w] + ["| " + " | ".join(c.replace("|", "/").replace("\n", " ") for c in r_) + " |" for r_ in rows[1:]]
        return "\n".join(md), None
    if "docs.google.com/presentation" in url:
        r = ctx.request.get(f"https://docs.google.com/presentation/d/{fid}/export/txt", timeout=120000)
        return (r.text() if r.ok else None), None
    r = ctx.request.get(f"https://drive.google.com/uc?export=download&id={fid}", timeout=120000)
    if not r.ok or "text/html" in r.headers.get("content-type", ""):
        return None, None
    body = r.body()
    if body[:4] == b"%PDF":
        doc = pymupdf.open(stream=body, filetype="pdf")
        return "\n".join(p.get_text() for p in doc), body
    return None, None


def write_index(course, cname, cid, entries, cache, posts=()):
    cdir = VAULT / "Courses" / course
    out = [f"# 📚 {course}: Class Materials", "",
           f"> Everything on the Classroom **Classwork** page for *{cname}*, captured {datetime.now():%a %-m/%-d %-I:%M %p}. "
           f"Tutor: search this for what {{NAME}} needs (e.g. \"guided notes\", \"Chapter 6\"), then fetch the attachment with "
           f"`tools/sync/fetch.py` and use it directly. Syllabus and schedule: [[Syllabus & Schedule]].", ""]
    topic = None
    for e in entries:
        c = cache.get(e["id"], {})
        kind, title, when = entry_fields(e)
        if e["topic"] != topic:
            topic = e["topic"]
            out += ["", f"## {topic or 'No topic'}", ""]
        url = c.get("url") or f"{CLASSROOM}/w/{cid}/t/all"
        icon = {"Material": "📘", "Question": "❓"}.get(kind.replace("Completed ", ""), "📝")
        done = " ✔" if kind.startswith("Completed") else ""
        out.append(f"- {icon} **[{title}]({url})**{done} · {kind.replace('Completed ', '')} · {when}")
        desc = [l for l in c.get("instructions", []) if not re.fullmatch(r"(Posted|Edited)?\s*\w{3} \d{1,2}", l)]
        if desc:
            out.append(f"  - {' / '.join(desc)[:300]}")
        for a in c.get("attachments", []):
            if not a.get("local"):                     # downloaded earlier (e.g. fetched when {{NAME}} asked for help)?
                stem = re.sub(r"\.(pdf|docx?|pptx?)$", "", a["name"], flags=re.I).lower()
                hit = next((f for f in (cdir / "_sources").rglob("*") if f.is_file()
                            and re.sub(r"\.(pdf|docx?|pptx?)$", "", f.name, flags=re.I).lower() == stem), None)
                if hit:
                    a["local"] = str(hit.relative_to(VAULT))
            local = f" · local: [[{a['local']}]]" if a.get("local") else ""
            out.append(f"  - 📎 [{a['name']}]({a['url']}){local}")
    if posts:
        out += ["", "## 📣 From the class stream (teacher posts)", "",
                "*Some teachers post assignments, readings and files here instead of on Classwork. Newest first.*", ""]
        for p in posts:
            first = " / ".join(p["body"])[:300]
            out.append(f"- **{p['date'] or 'undated'}**: {first}")
            for a in p["links"][:8]:
                out.append(f"  - 📎 [{a['name'] or a['url']}]({a['url']})")
    if not entries and not posts:
        out.append("*Nothing on Classwork or the stream yet.*")
    (cdir / "Class Materials.md").write_text("\n".join(out) + "\n")


def write_syllabus(course, cname, docs):
    cdir = VAULT / "Courses" / course
    out = [f"# 🗓️ {course}: Syllabus & Schedule", "",
           f"> From the syllabus / schedule documents posted on Classroom for *{cname}* (captured "
           f"{datetime.now():%a %-m/%-d}). Tutor: read this before helping with {course}: it has the teacher's "
           f"policies, units, pacing and dates. The originals are linked under each heading.", ""]
    if not docs:
        out += ["*No syllabus or schedule document found on Classwork yet.* The Course Map and the class stream are "
                "the best sources for now.", ""]
    for d in docs:
        out += [f"## {d['name']}", f"*From Classroom item \"{d['item']}\" · [original]({d['url']})"
                + (f" · local copy: [[{d['local']}]]" if d.get("local") else "") + "*", ""]
        out += [d["text"].strip() if d.get("text") else "*(couldn't extract text: open the original)*", ""]
    (cdir / "Syllabus & Schedule.md").write_text("\n".join(out) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    cfg = load_json(CONFIG_FILE, {})
    state = load_json(SYNC_DIR / "state.json", {})
    names = state.get("class_names", {})
    cache = load_json(CACHE, {})
    with profile_lock(), sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(str(PROFILE_DIR), channel="chrome", headless=True,
                                                    ignore_default_args=KEEP_KEYCHAIN)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            home = read(page, CLASSROOM + "/h", 1)
            BOILER.update(l.strip() for l in home["text"].split("\n") if l.strip())
            for spec in cfg.get("classes", []):
                course = spec["course"]
                if a.course and a.course != course:
                    continue
                cid = next((c for c, n in names.items() if spec["match"].lower() in n.lower()), None)
                if not cid:
                    log(f"classindex: {course}: class id unknown (run collect.py first)")
                    continue
                (VAULT / "Courses" / course).mkdir(parents=True, exist_ok=True)
                entries = classwork_entries(page, cid)
                opened = 0
                for e in entries:
                    kind, title, when = entry_fields(e)
                    c = cache.get(e["id"])
                    if c and c.get("when") == when and not a.refresh:
                        continue
                    path = KIND_PATH.get(kind, "m")
                    url = f"{CLASSROOM}/c/{cid}/{path}/{b64(e['id'])}/details"
                    try:
                        d = parse_details(read(page, url, 0.5))
                    except NeedsLogin:
                        raise SystemExit("session expired: run tools/sync/login.py")
                    except Exception as ex:
                        log(f"classindex: {course}: {title}: {str(ex)[:100]}")
                        continue
                    for att in d["attachments"]:
                        att["kind"] = kind_of(att["url"])
                    cache[e["id"]] = {"course": course, "title": title, "kind": kind, "when": when, "url": url,
                                      "topic": e["topic"], "instructions": d["instructions"],
                                      "attachments": d["attachments"]}
                    opened += 1
                try:
                    posts = stream_entries(page, cid)
                except NeedsLogin:
                    raise SystemExit("session expired: run tools/sync/login.py")
                write_index(course, names[cid], cid, entries, cache, posts)
                # syllabus / schedule documents: download and convert to text
                docs = []
                candidates = []
                for e in entries:
                    c = cache.get(e["id"], {})
                    if SYLLABUS_RE.search(c.get("title", "")):
                        candidates.append((c["title"], c.get("attachments", [])))
                for p in posts:
                    text = " ".join(p["body"])
                    for l in p["links"]:
                        l.setdefault("kind", kind_of(l["url"]))
                    if SYLLABUS_RE.search(text) or any(SYLLABUS_RE.search(l["name"]) for l in p["links"]):
                        candidates.append((f"stream post {p['date']}", [l for l in p["links"]
                                           if SYLLABUS_RE.search(l["name"]) or len(p["links"]) == 1]))
                seen_urls = set()
                for item_title, atts in candidates:
                    for att in atts:
                        if att["url"] in seen_urls or SUBMISSION_RE.search(att.get("name", "")):
                            continue
                        seen_urls.add(att["url"])
                        if att.get("kind") in ("form", "video", "web"):
                            continue
                        try:
                            text, pdf = doc_text(ctx, att["url"])
                        except Exception as ex:
                            text, pdf = None, None
                            log(f"classindex: {course}: couldn't fetch {att['name']}: {str(ex)[:80]}")
                        local = None
                        if pdf:
                            f = VAULT / "Courses" / course / "_sources" / "syllabus" / re.sub(r'[\\/:*?"<>|]+', "-", att["name"])
                            f.parent.mkdir(parents=True, exist_ok=True)
                            f.write_bytes(pdf)
                            local = str(f.relative_to(VAULT))
                            att["local"] = local
                        docs.append({"name": att["name"], "item": item_title, "url": att["url"], "text": text,
                                     "local": local})
                write_syllabus(course, names[cid], docs)
                write_index(course, names[cid], cid, entries, cache, posts)
                log(f"classindex: {course}: {len(entries)} items ({opened} opened), {len(docs)} syllabus/schedule doc(s)")
                print(f"{course}: {len(entries)} items ({opened} opened), {len(docs)} syllabus/schedule doc(s)")
                save_json(CACHE, cache)
        finally:
            ctx.close()
    save_json(CACHE, cache)


if __name__ == "__main__":
    main()
