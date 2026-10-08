"""Build Classes.md (the one-page class database) from each Courses/<course>/Class Profile.md frontmatter.
  ~/miniconda3/envs/study/bin/python tools/classes_table.py"""
import re
from datetime import date
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent


def props(path):
    m = re.match(r"^---\n(.*?)\n---", path.read_text(), re.S)
    out = {}
    for line in (m.group(1) if m else "").split("\n"):
        k, _, v = line.partition(":")
        if v:
            out[k.strip()] = v.strip().strip('"')
    return out


rows = []
for f in sorted(VAULT.glob("Courses/*/Class Profile.md")):
    p = props(f)
    c = f.parent.name
    rows.append((c, p))
out = ["# 🏫 My Classes", "",
       f"> One row per core class, built from each class's **Class Profile** (updated {date.today():%b %-d}). "
       "Tutor: open the class's profile before helping. For due dates see [[To-Do]].", "",
       "| Class | Teacher | Now | Next assessment | Late work | AI rule | Grading |", "|---|---|---|---|---|---|---|"]
for c, p in rows:
    esc = lambda s: (s or "").replace("|", "/")
    out.append(f"| [[Courses/{c}/Class Profile\\|{c}]] | {esc(p.get('teacher'))} | {esc(p.get('current_unit'))} | "
               f"**{esc(p.get('next_assessment'))}** | {esc(p.get('late_work'))} | {esc(p.get('ai_policy'))} | {esc(p.get('grading'))} |")
out += ["", "## Where each class posts work", ""]
out += [f"- **{c}**: {p.get('posts_work_on', '')}" for c, p in rows]
out += ["", "## Contacts", ""]
out += [f"- **{c}**: {p.get('teacher', '')} · {p.get('contact', '')}" for c, p in rows]
(VAULT / "Classes.md").write_text("\n".join(out) + "\n")
print(f"Classes.md: {len(rows)} classes")
