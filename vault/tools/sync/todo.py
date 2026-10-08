"""{{NAME}}'s To-Do tracker: `To-Do.md` at the vault root, fed by /sync.

  todo.py from-snapshot <Inbox/sync/DIR>        add/update Classroom work; tick off what Classroom says is turned in
  todo.py add --course C --title T [--due YYYY-MM-DD[ HH:MM]] [--kind test|task] [--url U] [--note PATH]
  todo.py done <id or title substring> [--reason R]
  todo.py render                                re-sort, re-flag overdue, pick up boxes {{NAME}} ticked in Obsidian
  todo.py list [--json]                         open school tasks

Source of truth for school tasks: Inbox/sync/todo.json. `To-Do.md` is regenerated from it, but:
  * the "✍️ My tasks" section is {{NAME}}'s and is copied through untouched;
  * boxes {{NAME}} ticks (or unticks) in To-Do.md are read back first, so his changes always win.
"""
import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from common import CONFIG_FILE, SYNC_DIR, VAULT, load_json, save_json
from work import as_past, classwork_items, ref_date, short_class, todo_page_items

TODO_MD = VAULT / "To-Do.md"
TODO_JSON = SYNC_DIR / "todo.json"
SCHOOL_H, MINE_H, DONE_H = "## 📚 School (from Classroom)", "## ✍️ My tasks", "## ✔️ Done"
COLLEGE_H = "## 🎓 College applications"     # course "College": counselor posts (college_posts.py) + deadlines (tools/college)
ID_RE = re.compile(r"%%id:(.+?)%%")
KEEP_DONE = 40


# ---------- storage ----------

def load():
    return load_json(TODO_JSON, {"items": {}})


def save(db):
    save_json(TODO_JSON, db)


def upsert(db, iid, **f):
    it = db["items"].get(iid)
    if it is None:
        db["items"][iid] = {"status": "open", "added": date.today().isoformat(), **{k: v for k, v in f.items() if v is not None}}
        return "added"
    for k, v in f.items():
        if v is not None:
            it[k] = v
    return "updated"


def mark_done(db, iid, reason):
    it = db["items"].get(iid)
    if it and it["status"] == "open":
        it.update(status="done", done_at=date.today().isoformat(), done_reason=reason)
        return True
    return False


# ---------- helpers ----------

def course_for(class_name, cfg):
    for spec in cfg.get("classes", []):
        if spec["match"].lower() in class_name.lower():
            return spec["course"]
    return None


def note_for(course, title):
    """Assignment note whose frontmatter title matches (created by /sync or /homework)."""
    folder = VAULT / "Courses" / course / "Assignments"
    if not folder.exists():
        return None, None
    for f in folder.glob("*.md"):
        head = f.read_text()[:800]
        m = re.search(r'^title:\s*"?(.+?)"?\s*$', head, re.M)
        if m and m.group(1).strip().lower() == title.strip().lower():
            src = re.search(r'^source:\s*"?(.+?)"?\s*$', head, re.M)
            return str(f.relative_to(VAULT).with_suffix("")), (src.group(1) if src else None)
    return None, None


def due_date(it):
    return date.fromisoformat(it["due"][:10]) if it.get("due") else None


# ---------- reading {{NAME}}'s edits back from To-Do.md ----------

def read_md():
    if not TODO_MD.exists():
        return {}, None
    text = TODO_MD.read_text()
    section, ticks, mine = None, {}, []
    for line in text.split("\n"):
        if line.startswith("## "):
            section = line.strip()
            continue
        if section == MINE_H:
            mine.append(line)
        m = ID_RE.search(line)
        if m and re.match(r"\s*- \[[ xX]\]", line):
            ticks[m.group(1)] = ("x" in line[:line.index("]")].lower(), section)
    while mine and not mine[-1].strip():
        mine.pop()
    return ticks, mine


def absorb_ticks(db):
    ticks, mine = read_md()
    for iid, (checked, section) in ticks.items():
        it = db["items"].get(iid)
        if not it:
            continue
        if checked and it["status"] == "open":
            it.update(status="done", done_at=date.today().isoformat(), done_reason="ticked by you")
        elif not checked and it["status"] == "done":
            it.update(status="open")
            it.pop("done_at", None)
            it.pop("done_reason", None)
    return mine


# ---------- rendering ----------

def fmt_line(iid, it, today):
    d = due_date(it)
    when = "No due date"
    if d:
        when = d.strftime("%a %-m/%-d")
        if len(it["due"]) > 10:
            t = datetime.strptime(it["due"][11:16], "%H:%M")
            when += " " + t.strftime("%-I:%M %p")
    flag = ""
    if it.get("missing") and it["status"] == "open":
        flag = "🚩 **Missing on Classroom** · "
    elif d and it["status"] == "open":
        if d < today:
            flag = "⚠️ **Overdue** · "
        elif d == today:
            flag = "🔴 **Today** · "
        elif d == today + timedelta(days=1):
            flag = "🟠 **Tomorrow** · "
    kind = "📝 " if it.get("kind") == "test" else ""
    title = it["title"]
    label = f"[[{it['note']}|{title}]]" if it.get("note") else title
    parts = [f"{flag}**{when}**", it.get("course") or "Other", f"{kind}{label}"]
    if it.get("url"):
        parts.append(f"[Classroom]({it['url']})")
    due_tag = f" 📅 {it['due'][:10]}" if it.get("due") else ""
    if it["status"] == "done":
        reason = f" ({it['done_reason']})" if it.get("done_reason") else ""
        return f"- [x] {it.get('course') or 'Other'} · {label} ✅ {it.get('done_at', '')}{reason} %%id:{iid}%%"
    return f"- [ ] {' · '.join(parts)}{due_tag} %%id:{iid}%%"


def render(db, mine=None):
    if mine is None:
        mine = absorb_ticks(db)
    today = date.today()
    open_all = [(i, it) for i, it in db["items"].items() if it["status"] == "open"]
    open_all.sort(key=lambda p: (due_date(p[1]) is None, p[1].get("due") or "", p[1].get("course") or ""))
    open_items = [p for p in open_all if p[1].get("course") != "College"]
    college = [p for p in open_all if p[1].get("course") == "College"]
    done = sorted(((i, it) for i, it in db["items"].items() if it["status"] == "done"),
                  key=lambda p: p[1].get("done_at", ""), reverse=True)
    for i, _ in done[KEEP_DONE:]:
        del db["items"][i]
    done = done[:KEEP_DONE]
    n_over = sum(1 for _, it in open_items if due_date(it) and due_date(it) < today)
    out = ["# ✅ To-Do", "",
           f"> **School** tasks are added and ticked off by `/sync` from Google Classroom (sorted by due date; "
           f"updated {datetime.now():%a %-m/%-d %-I:%M %p}). Tick a box yourself when you finish something, and it "
           f"moves to Done on the next sync. **My tasks** is yours: `/sync` never changes it.", ""]
    out += [SCHOOL_H, ""]
    if open_items:
        if n_over:
            out += [f"*{n_over} overdue: if you already turned it in, tick it.*", ""]
        out += [fmt_line(i, it, today) for i, it in open_items]
    else:
        out.append("*Nothing open. 🎉*")
    out += ["", COLLEGE_H, ""]
    out += [fmt_line(i, it, today) for i, it in college] or ["*Nothing open.*"]
    out += ["", MINE_H, ""]
    out += mine if mine else ["- [ ] "]
    out += ["", DONE_H, ""]
    out += [fmt_line(i, it, today) for i, it in done] or ["*Nothing yet.*"]
    TODO_MD.write_text("\n".join(out) + "\n")
    save(db)


# ---------- commands ----------

def from_snapshot(db, snap_dir):
    """Classroom's own lists decide what's open: the To-do ("Assigned") list plus the "Missing" list.
    Classwork pages only add due times and confirm "Completed" items; they never make anything open, because
    a Classwork page read before turn-in statuses load shows every assignment as not completed."""
    pages = load_json(Path(snap_dir) / "pages.json", None)
    if not pages:
        sys.exit(f"no pages.json in {snap_dir}")
    cfg = load_json(CONFIG_FILE, {})
    ref = ref_date(pages["when"])
    log = []

    # 1. what Classroom itself lists as not turned in
    open_now = {}
    for key, missing in (("todo", False), ("missing", True)):
        pg = pages.get(key)
        if not pg:
            continue
        for t in todo_page_items(pg["text"], ref):
            course = course_for(t["class_name"], cfg)
            if not course:
                if cfg.get("core_only"):
                    continue                    # clubs, homeroom, class-of lists: not tracked
                course = short_class(t["class_name"])
            due = as_past(t["due"], ref) if missing else t["due"]
            open_now[(course, t["title"])] = {"due": due, "missing": missing}
    lists_complete = bool(pages.get("todo_expanded")) and (
        "missing" not in pages or bool(pages.get("missing_expanded")))

    # 2. Classwork: exact due times, links, and confirmed completions
    cw = {}
    for course, e in pages.get("classes", {}).items():
        cls_url = f"https://classroom.google.com/w/{e['id']}/t/all" if e.get("id") else None
        for w in classwork_items(e["classwork"]["text"], ref):
            cw[(course, w["title"])] = (w, cls_url)
            if w["completed"] and e.get("status_loaded", True) and (course, w["title"]) not in open_now:
                if mark_done(db, f"cw:{course}:{w['title']}", "turned in on Classroom"):
                    log.append(f"✔ {course}: {w['title']}")

    # 3. add / refresh everything Classroom lists as open
    for (course, title), info in open_now.items():
        iid = f"cw:{course}:{title}"
        w, cls_url = cw.get((course, title), (None, None))
        due = info["due"] or (w["due"] if w else None)
        note, src = note_for(course, title)
        it = db["items"].get(iid)
        if it and it["status"] == "done" and it.get("done_reason") != "ticked by you":
            it.update(status="open")                 # Classroom says it's still not turned in
            it.pop("done_at", None)
            it.pop("done_reason", None)
            log.append(f"↺ {course}: {title} (Classroom still lists it as not turned in)")
        r = upsert(db, iid, course=course, title=title, due=due, note=note, url=src or cls_url,
                   source="classroom", missing=info["missing"])
        if r == "added":
            log.append(f"＋ {course}: {title} (due {due or '—'}){' 🚩 missing' if info['missing'] else ''}")

    # 4. anything Classroom no longer lists was turned in (only when both lists were read completely)
    if lists_complete:
        for iid, it in db["items"].items():
            if it["status"] == "open" and it.get("source") in ("classroom", "todo-page") \
                    and (it.get("course"), it["title"]) not in open_now:
                if mark_done(db, iid, "turned in (no longer on Classroom's To-do/Missing lists)"):
                    log.append(f"✔ {it.get('course')}: {it['title']}")
    else:
        log.append("⚠ Classroom's To-do/Missing lists weren't fully read this run: nothing was ticked off")
    return log


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("from-snapshot"); s.add_argument("dir")
    s = sub.add_parser("add")
    s.add_argument("--course", required=True); s.add_argument("--title", required=True)
    s.add_argument("--due"); s.add_argument("--kind", default="task"); s.add_argument("--url"); s.add_argument("--note")
    s = sub.add_parser("done"); s.add_argument("what"); s.add_argument("--reason", default="done")
    sub.add_parser("render")
    s = sub.add_parser("list"); s.add_argument("--json", action="store_true")
    a = ap.parse_args()

    db = load()
    mine = absorb_ticks(db)          # {{NAME}}'s ticks in Obsidian win over everything below
    if a.cmd == "from-snapshot":
        for l in from_snapshot(db, a.dir) or ["no changes"]:
            print(l)
    elif a.cmd == "add":
        slug = re.sub(r"\W+", "-", a.title.lower()).strip("-")
        iid = f"{a.kind}:{a.course}:{slug}" + (f":{a.due[:10]}" if a.due else "")
        print(upsert(db, iid, course=a.course, title=a.title, due=a.due, kind=a.kind, url=a.url, note=a.note,
                     source="manual"), iid)
    elif a.cmd == "done":
        hits = [i for i, it in db["items"].items() if it["status"] == "open"
                and (i == a.what or a.what.lower() in it["title"].lower())]
        if len(hits) != 1:
            sys.exit(f"{len(hits)} open tasks match {a.what!r}: " + "; ".join(db['items'][h]['title'] for h in hits))
        mark_done(db, hits[0], a.reason)
        print("done:", db["items"][hits[0]]["title"])
    elif a.cmd == "list":
        items = {i: it for i, it in db["items"].items() if it["status"] == "open"}
        if a.json:
            print(json.dumps(items, indent=2, ensure_ascii=False))
        else:
            for i, it in sorted(items.items(), key=lambda p: p[1].get("due") or "9999"):
                print(f"{it.get('due') or 'no due date':16} {it.get('course') or '':12} {it['title']}")
        return
    render(db, mine)


if __name__ == "__main__":
    main()
