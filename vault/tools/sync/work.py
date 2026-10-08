"""Parse Classroom page text (as saved in a snapshot's pages.json) into work items with due dates."""
import re
from datetime import date, datetime, timedelta

MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
WORK_KINDS = {"Assignment": False, "Completed Assignment": True, "Question": False, "Completed Question": True,
              "Quiz assignment": False, "Completed Quiz assignment": True}
TODO_SECTIONS = {"No due date", "This week", "Last week", "Next week", "Later", "Earlier", "Missing"}
TODO_MARKERS = {"assignment", "question", "quiz", "live_help", "assignment_late", "help"}   # icon names before each To-do item
ICON_WORDS = {"assignment", "book", "quiz", "help", "live_help", "assignment_turned_in", "assignment_late"}


def clean(s):
    return s.replace(" ", " ").replace("\xa0", " ").strip()


def parse_due(text, ref):
    """'Due Tomorrow, 8:00 AM' / 'Sep 29' / 'Friday, 11:59 PM' / 'Due 8:00 AM' -> 'YYYY-MM-DD[ HH:MM]' or None."""
    t = clean(text)
    t = re.sub(r"^Due\s+", "", t, flags=re.I)
    if not t or re.match(r"no due date", t, re.I):
        return None
    tm = re.search(r"(\d{1,2}):(\d{2})\s*([AP]M)", t, re.I)
    hhmm = None
    if tm:
        h = int(tm.group(1)) % 12 + (12 if tm.group(3).upper() == "PM" else 0)
        hhmm = f"{h:02d}:{tm.group(2)}"
    head = t.split(",")[0].strip().lower()
    d = None
    md = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:,\s*(\d{4}))?", t.lower())
    if md:                                   # an explicit month/day wins ("Sunday, Oct 18")
        y = int(md.group(3)) if md.group(3) else ref.year
        d = date(y, MONTHS[md.group(1)], int(md.group(2)))
        if not md.group(3) and (d - ref).days < -200:       # "Jan 5" seen in December means next year
            d = date(y + 1, d.month, d.day)
    elif head in ("today",) or (tm and head == clean(tm.group(0)).lower()):
        d = ref
    elif head == "tomorrow":
        d = ref + timedelta(days=1)
    elif head == "yesterday":
        d = ref - timedelta(days=1)
    elif head in DAYS:
        delta = (DAYS.index(head) - ref.weekday()) % 7
        d = ref + timedelta(days=delta or 7)
    else:
        m = re.match(r"([a-z]{3})[a-z]*\s+(\d{1,2})(?:,\s*(\d{4}))?", head)
        if m and m.group(1) in MONTHS:
            y = int(m.group(3)) if m.group(3) else ref.year
            d = date(y, MONTHS[m.group(1)], int(m.group(2)))
            if not m.group(3) and (d - ref).days < -200:      # "Jan 5" seen in December means next year
                d = date(y + 1, d.month, d.day)
    if not d:
        return None
    return d.isoformat() + (f" {hhmm}" if hhmm else "")


def classwork_items(text, ref):
    """From a class's Classwork page: [{title, due, completed}] for assignments/questions (not materials)."""
    L = [clean(l) for l in text.split("\n") if clean(l)]
    out = []
    for i, l in enumerate(L):
        if l not in WORK_KINDS:
            continue
        j = i + 1
        while j < len(L) and L[j].lower() in ICON_WORDS:
            j += 1
        if j >= len(L):
            continue
        title = L[j]
        due = None
        for k in range(j + 1, min(j + 4, len(L))):
            if L[k].startswith("Due ") or L[k].lower() == "no due date":
                due = parse_due(L[k], ref)
                break
            if L[k] in WORK_KINDS or L[k] == "Material":
                break
        out.append({"title": title, "due": due, "completed": WORK_KINDS[l]})
    return out


def as_past(due, ref):
    """Classroom's Missing list only holds past-due work: 'Monday' means last Monday, 'Mar 1' means this past March."""
    if not due:
        return due
    d = date.fromisoformat(due[:10])
    while d > ref:
        d = d - timedelta(days=7) if (d - ref).days <= 7 else date(d.year - 1, d.month, d.day)
    return d.isoformat() + due[10:]


def todo_page_items(text, ref):
    """From the To-do (not turned in) page: [{title, class_name, due}]. Sections must be expanded to be read."""
    L = [clean(l) for l in text.split("\n") if clean(l)]
    out, section = [], None
    for i, l in enumerate(L):
        if l in TODO_SECTIONS:
            section = l
            continue
        if l.lower() in TODO_MARKERS and i + 2 < len(L):
            title, cls = L[i + 1], L[i + 2]
            nxt = L[i + 3] if i + 3 < len(L) else ""
            dated = section != "No due date" and nxt.lower() not in TODO_MARKERS \
                and not re.match(r"(posted|edited)\b", nxt, re.I)
            due = parse_due(nxt, ref) if dated else None
            if (title, cls) not in {(o["title"], o["class_name"]) for o in out}:   # sections are read more than once
                out.append({"title": title, "class_name": cls, "due": due})
    return out


def short_class(name):
    """'SY26-27 - AS1 AP Statistics - Smith - 001' -> 'AP Statistics'; '8 - Asian-American Literature (Honors)' -> ..."""
    n = re.sub(r"^SY\d{2}-\d{2}\s*-\s*(AS\d|HS\d)?\s*", "", name)
    n = re.sub(r"^\d+\s*-\s*", "", n)
    n = re.sub(r"\s*-\s*[A-Z][a-z]+\s*-\s*[\w]+$", "", n)       # " - Teacher - section"
    n = re.sub(r"\s+\d{2}-\d{2}$|\s+\d{4}-\d{4}$", "", n)      # trailing school year
    return n.strip() or name


def ref_date(snapshot_when):
    return datetime.fromisoformat(snapshot_when).date()
