"""Read section C7 ("relative importance of admission factors") from a college's official Common Data Set PDF.

  ~/miniconda3/envs/study/bin/python tools/college/cds.py <pdf-or-url> [--school "Name"] [--write]

Prints the 18–19 factors with Very Important / Important / Considered / Not Considered. With --write, stores the
table in College/Schools/<School>.md between the CDS markers (the school note must exist). Only use the college's
OWN CDS file (usually on its institutional research site): aggregator sites have been wrong (checked 2026-10-01:
one listed Michigan's essay as "Very Important"; Michigan's own CDS says "Important").
"""
import argparse
import re
import sys
import tempfile
import urllib.request
from datetime import date
from pathlib import Path

import pymupdf

VAULT = Path(__file__).resolve().parents[2]
LEVELS = ["Very Important", "Important", "Considered", "Not Considered"]
FACTORS = ["Rigor of secondary school record", "Class rank", "Academic GPA", "Standardized test scores",
           "Application Essay", "Recommendation", "Interview", "Extracurricular activities", "Talent/ability",
           "Character/personal qualities", "First generation", "Alumni/ae relation", "Geographical residence",
           "State residency", "Religious affiliation/commitment", "Racial/ethnic status", "Volunteer work",
           "Work experience", "Level of applicant's interest"]
CHECKED, UNCHECKED = set("☒☑■✔✓✗xX"), set("☐□")


def norm(s):
    return re.sub(r"[^a-z]", "", s.lower().replace("’", "'"))


def fetch(src):
    if re.match(r"https?://", src):
        ext = ".xlsx" if ".xlsx" in src.lower() else ".pdf"
        tmp = Path(tempfile.mkdtemp()) / f"cds{ext}"
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129 Safari/537.36", "Accept": "*/*"})
        tmp.write_bytes(urllib.request.urlopen(req, timeout=60).read())
        return tmp
    return Path(src)


def from_xlsx(path):
    """Some schools (e.g. UIUC) publish the CDS as a spreadsheet: find the C7 header row, then the X in each row."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    for ws in wb.worksheets:
        cols, res = None, {}
        for row in ws.iter_rows(values_only=True):
            cells = ["" if v is None else str(v).strip() for v in row]
            low = [c.lower() for c in cells]
            if "very important" in low and "not considered" in low:
                cols = {LEVELS[k]: low.index(LEVELS[k].lower()) for k in range(4)}
                continue
            if cols:
                key = match_factor(" ".join(c for i, c in enumerate(cells) if i < min(cols.values())))
                hits = [lvl for lvl, i in cols.items() if i < len(cells) and cells[i] and cells[i] not in UNCHECKED]
                if key and len(hits) == 1:
                    res[key] = hits[0]
                if len(res) >= 18:
                    break
        if len(res) >= 12:
            return res
    return {}


def c7_page(doc):
    for p in doc:
        t = p.get_text()
        if "C7" in t and "Rigor" in t and ("Very Important" in t or "Very important" in t):
            return p
    return None


def by_boxes(text):
    """Filled-form CDS: each factor label is followed by four boxes, one of them checked."""
    label, res, boxes = "", {}, []
    for t in (x.strip() for x in text.split("\n")):
        chars = [c for c in t if c in CHECKED | UNCHECKED]
        if chars and len(t.replace(" ", "")) == len(chars):
            boxes += chars
            if len(boxes) == 4:
                key = match_factor(label)
                if key and sum(c in CHECKED for c in boxes) == 1:
                    res[key] = LEVELS[[c in CHECKED for c in boxes].index(True)]
                label, boxes = "", []
            continue
        boxes = []
        label = (label + " " + t)[-160:]      # labels wrap; section headings ("Nonacademic") come before them
    return res


def by_columns(page):
    """Table with X marks: map each mark's x-position to the nearest column header."""
    words = page.get_text("words")
    heads = {}
    for w in words:
        if w[4].lower() == "very":
            heads.setdefault("Very Important", (w[0] + w[2]) / 2 + 20)
    # "Important" (not preceded by Very), "Considered" (not preceded by Not), "Not"
    imp = [w for w in words if w[4].lower() == "important"]
    con = [w for w in words if w[4].lower() == "considered"]
    nots = [w for w in words if w[4].lower() == "not"]
    if not (heads and imp and con and nots):
        return {}
    top = min(w[1] for w in imp)
    hdr = [w for w in words if abs(w[1] - top) < 25]
    xs = sorted(((w[0] + w[2]) / 2, w[4].lower()) for w in hdr if w[4].lower() in ("very", "important", "considered", "not"))
    cols = []
    for x, t in xs:
        if t == "very":
            cols.append(("Very Important", x + 20))
        elif t == "not":
            cols.append(("Not Considered", x + 15))
        elif t == "important" and not any(c[0] == "Very Important" and abs(c[1] - x) < 40 for c in cols):
            cols.append(("Important", x))
        elif t == "considered" and not any(c[0] == "Not Considered" and abs(c[1] - x) < 40 for c in cols):
            cols.append(("Considered", x))
    res = {}
    lines = {}
    for w in words:
        if w[1] > top + 5:
            lines.setdefault(round(w[1] / 4), []).append(w)
    for ws in lines.values():
        ws.sort(key=lambda w: w[0])
        label = " ".join(w[4] for w in ws if w[4] not in CHECKED and w[0] < cols[0][1] - 40)
        marks = [w for w in ws if w[4] in CHECKED or w[4].lower() == "x"]
        key = match_factor(label)
        if key and len(marks) == 1:
            mx = (marks[0][0] + marks[0][2]) / 2
            res[key] = min(cols, key=lambda c: abs(c[1] - mx))[0]
    return res


def match_factor(label):
    """The factor whose name the (rolling) label text ends with; else the longest one it contains."""
    n = norm(label)
    if not n:
        return None
    ends = [f for f in FACTORS if n.endswith(norm(f))]
    if ends:
        return max(ends, key=len)
    inside = [f for f in FACTORS if norm(f) in n]
    return max(inside, key=len) if inside else None


def table_md(school, res, source):
    rows = ["| Factor | Rating |", "|---|---|"]
    for f in FACTORS:
        if f in res:
            r = res[f]
            badge = {"Very Important": "🟥 Very important", "Important": "🟧 Important",
                     "Considered": "🟨 Considered", "Not Considered": "⬜ Not considered"}[r]
            rows.append(f"| {f} | {badge} |")
    return (f"<!-- CDS:start -->\n**Common Data Set C7** (how {school} weighs each factor; from its own CDS, "
            f"[source]({source}), read {date.today().isoformat()}):\n\n" + "\n".join(rows) + "\n<!-- CDS:end -->")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--school")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    path = fetch(a.src)
    if path.suffix == ".xlsx":
        res = from_xlsx(path)
        if len(res) < 12:
            sys.exit(f"only parsed {len(res)} factors from the spreadsheet: open it and read C7 by hand")
        report(res, a, "spreadsheet")
        return
    doc = pymupdf.open(path)
    page = c7_page(doc)
    if not page:
        sys.exit("couldn't find section C7 in this PDF (is it the full CDS, or only another section?)")
    res = by_boxes(page.get_text())
    if len(res) < 12:
        res2 = by_columns(page)
        if len(res2) > len(res):
            res = res2
    if len(res) < 12:
        print(page.get_text()[:3000])
        sys.exit(f"only parsed {len(res)} factors: read the page text above by hand (or render the page)")
    report(res, a, f"page {page.number + 1}")


def report(res, a, where):
    for f in FACTORS:
        if f in res:
            print(f"{res[f]:15}  {f}")
    print(f"({len(res)} factors, {where})")
    if a.write:
        if not a.school:
            sys.exit("--write needs --school")
        note = VAULT / "College" / "Schools" / f"{a.school}.md"
        s = note.read_text()
        block = table_md(a.school, res, a.src)
        if "<!-- CDS:start -->" in s:
            s = re.sub(r"<!-- CDS:start -->.*?<!-- CDS:end -->", lambda m: block, s, flags=re.S)
        else:
            s = s.rstrip() + "\n\n## 📊 What they weigh (CDS C7)\n" + block + "\n"
        note.write_text(s)
        print(f"written to {note.relative_to(VAULT)}")


if __name__ == "__main__":
    main()
