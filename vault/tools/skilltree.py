"""Skill trees: one Obsidian Canvas per class, colored by what {{NAME}} actually knows.

  ~/miniconda3/envs/study/bin/python tools/skilltree.py "AP Calc BC"     # one class
  ~/miniconda3/envs/study/bin/python tools/skilltree.py --all            # every class with a spec

Inputs per class (Courses/<course>/):
  _skilltree.yaml     the tree's shape: branches (units) and nodes (skills) with prerequisites (`needs`),
                      which Learner Model rows they read (`lm`), and words to find them in notes (`find`)
  Learner Model.md    the levels (⬜ 🟥 🟨 🟩 ⭐), last seen, notes; the tutor updates it after every session
Outputs:
  Skill Tree.canvas   the map: cards colored by level, prerequisite arrows, links to every note that mentions the skill
  .skilltree.json     previous levels, to mark "✨ leveled up" for a week
  Skill Trees.md      (vault root) one progress bar per class, embedded on the Dashboard

A Learner Model row that no node reads yet is added to the spec automatically (branch "new"), so a newly learned
skill always appears on the map; the tutor then gives it a proper branch and prerequisites.
"""
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

VAULT = Path(__file__).resolve().parent.parent
COURSES = VAULT / "Courses"
LEVELS = {"⬜": 0, "🟥": 1, "🟨": 2, "🟩": 3, "⭐": 4}
NAMES = {-1: "Ahead", 0: "Not checked yet", 1: "Shaky", 2: "Developing", 3: "Solid", 4: "Mastered"}
# canvas colors: "1" red · "2" orange · "3" yellow · "4" green · "5" cyan · "6" purple, or hex
COLOR = {4: "#d4a017", 3: "4", 2: "3", 1: "1", 0: None}
READY = "5"
SKIP_FILES = {"Course Map.md", "Learner Model.md", "Class Materials.md", "Syllabus & Schedule.md", "Class Profile.md"}
W, GX, GY, PAD = 340, 90, 34, 50
MAXCOL = 6


# ---------- reading ----------

def norm(s):
    s = re.sub(r"\$[^$]*\$", " ", s)          # drop inline math
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def learner_rows(course):
    p = COURSES / course / "Learner Model.md"
    if not p.exists():
        return []
    rows = []
    for line in p.read_text().split("\n"):
        if not line.startswith("| ") or "---" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        lvl = next((i for i, c in enumerate(cells) if c in LEVELS), None)
        if lvl is None:
            continue
        seen = next((c for c in cells[lvl + 1:] if re.fullmatch(r"\d{4}-\d{2}-\d{2}", c)), "")
        notes = cells[-1] if len(cells) > lvl + 2 else ""
        rows.append({"concept": cells[0], "level": LEVELS[cells[lvl]], "seen": seen,
                     "guided": "not checked" in notes or "guided" in notes.lower(), "notes": notes})
    return rows


def row_matches(row, key):
    """`lm` keys are the start of the Learner Model's concept text, copied exactly (math included)."""
    c = row["concept"]
    return c.startswith(key) or (bool(norm(key)) and norm(c) == norm(key))


def notes_for(course):
    """Every note in the class folder that could mention a skill (sessions, assignments, summaries, flashcards…)."""
    out = []
    for f in (COURSES / course).rglob("*.md"):
        rel = f.relative_to(COURSES / course)
        if rel.parts[0].startswith("_") or f.name in SKIP_FILES or f.name.startswith("Skill Tree"):
            continue
        m = re.match(r"(\d{4}-\d{2}-\d{2})", f.name)
        when = m.group(1) if m else datetime.fromtimestamp(f.stat().st_mtime).date().isoformat()
        out.append((when, f, f.read_text(errors="ignore").lower()))
    out.sort(key=lambda t: t[0], reverse=True)
    return out


def mentions(node, notes):
    pats = [p.lower() for p in node.get("find", []) if p]
    hits = []
    for when, f, text in notes:
        if any(p in text for p in pats):
            hits.append((when, f))
    return hits


# ---------- spec ----------

def load_spec(course):
    p = COURSES / course / "_skilltree.yaml"
    return (yaml.safe_load(p.read_text()) if p.exists() else None), p


def adopt_new_rows(spec, path, rows):
    """Learner Model rows no node reads → new nodes in the spec (appended as text so comments survive)."""
    used = [k for n in spec["nodes"] for k in n.get("lm", [])]
    fresh = [r for r in rows if not any(row_matches(r, k) for k in used)]
    if not fresh:
        return []
    added, ids = [], {n["id"] for n in spec["nodes"]}
    text = path.read_text().rstrip() + "\n"
    if not any(b["id"] == "new" for b in spec["branches"]):
        spec["branches"].append({"id": "new", "name": "🆕 New skills (place me)"})
        text = text.replace("\nnodes:", '\n  - {id: new, name: "🆕 New skills (place me)"}\nnodes:', 1)
    text += "  # --- added automatically from the Learner Model: give each a real branch + needs ---\n"
    for r in fresh:
        label = re.sub(r"\$[^$]*\$", "", r["concept"]).strip(" ,;:()") or r["concept"]
        nid = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:40] or "skill"
        while nid in ids:
            nid += "-2"
        ids.add(nid)
        node = {"id": nid, "label": label[:60], "branch": "new", "lm": [r["concept"][:60]],
                "find": [label.lower()[:40]], "needs": []}
        spec["nodes"].append(node)
        added.append(label)
        text += "  - " + yaml.safe_dump(node, allow_unicode=True, default_flow_style=True, width=1000).strip() + "\n"
    path.write_text(text)
    return added


# ---------- computing ----------

def resolve(spec, rows):
    for n in spec["nodes"]:
        matched = [r for r in rows if any(row_matches(r, k) for k in n.get("lm", []))]
        n["rows"] = matched
        if matched:
            n["level"] = min(r["level"] for r in matched)          # honest: the weakest part counts
            n["seen"] = max((r["seen"] for r in matched), default="")
            n["guided"] = any(r["guided"] for r in matched) and n["level"] <= 2
        elif n.get("given") is not None:                         # known from class, never tutored
            n["level"], n["seen"], n["guided"] = int(n["given"]), "", False
        else:
            n["level"], n["seen"], n["guided"] = -1, "", False
    by = {n["id"]: n for n in spec["nodes"]}
    for n in spec["nodes"]:
        n["needs"] = [x for x in n.get("needs", []) if x in by]
        if n["level"] <= 0:
            n["ready"] = all(by[x]["level"] >= 2 for x in n["needs"])
    return by


def bar(frac, width=12):
    k = round(frac * width)
    return "▰" * k + "▱" * (width - k)


def progress(nodes):
    """Mastery %: each skill counts 0 (ahead/unknown) … 4 (mastered)."""
    if not nodes:
        return 0.0
    return sum(max(n["level"], 0) for n in nodes) / (4 * len(nodes))


def short(f):
    s = f.stem
    s = re.sub(r"^(\d{4})-(\d{2})-(\d{2}) ", lambda m: f"{int(m.group(2))}/{int(m.group(3))} ", s)
    return s if len(s) <= 34 else s[:32] + "…"


def card_text(n, by, hits, state, today):
    lvl = n["level"]
    if lvl < 0:
        icon = "🔓" if n.get("ready") else "🔒"
    else:
        icon = "⬜🟥🟨🟩⭐"[lvl]
    lines = [f"### {icon} {n['label']}"]
    meta = []
    if lvl < 0:
        meta.append("**Ready to learn**" if n.get("ready") else "*Locked*")
    else:
        meta.append(f"**{NAMES[lvl]}**" + (" · *guided, not checked*" if n.get("guided") else "")
                    + (f" · *{n.get('given_note', 'from class')}*" if not n.get("rows") and n.get("given") is not None else ""))
    if n.get("ref"):
        meta.append(f"`{n['ref']}`")
    if n.get("seen"):
        d = date.fromisoformat(n["seen"])
        meta.append(f"seen {d.month}/{d.day}")
    lines.append(" · ".join(meta))
    st = state.get(n["id"], {})
    if st.get("up") and today - date.fromisoformat(st["up"]) <= timedelta(days=7):
        d = date.fromisoformat(st["up"])
        lines.append(f"✨ *new progress {d.month}/{d.day}*")
    if lvl < 0 and not n.get("ready") and n["needs"]:
        blockers = [by[x]["label"] for x in n["needs"] if by[x]["level"] < 2]
        if blockers:
            lines.append("needs: " + ", ".join(blockers[:2]) + ("…" if len(blockers) > 2 else ""))
    other = [by[x] for x in n["needs"] if by[x]["branch"] != n["branch"]]
    if other and (lvl >= 0 or n.get("ready")):
        word = "↖ builds on" if lvl >= 0 else "🔑 unlocked by"
        lines.append(f"{word}: " + ", ".join(o["label"] for o in other[:2]) + ("…" if len(other) > 2 else ""))
    if n.get("tip"):
        lines.append(f"*{n['tip']}*")
    if hits:
        links = [f"[[{f.relative_to(VAULT).with_suffix('')}|{short(f)}]]" for _, f in hits[:4]]
        more = f" *+{len(hits) - 4}*" if len(hits) > 4 else ""
        lines.append("📝 " + " · ".join(links) + more)
    return "\n".join(lines)


def est_height(text):
    h = 30
    for line in text.split("\n"):
        chars = len(re.sub(r"\[\[[^|\]]*\|([^\]]*)\]\]", r"\1", line))
        h += 26 * max(1, -(-chars // 38))
    return max(110, h + 10)


def layout(spec, by):
    """Branches are horizontal bands (in curriculum order); inside a band, a skill sits one column right of the
    deepest prerequisite in the same band."""
    bands = [b for b in spec["branches"] if any(n["branch"] == b["id"] for n in spec["nodes"])]
    depth = {}

    def d(nid, stack=()):
        if nid in depth:
            return depth[nid]
        n = by[nid]
        same = [x for x in n["needs"] if by[x]["branch"] == n["branch"] and x not in stack]
        depth[nid] = 0 if not same else 1 + max(d(x, stack + (nid,)) for x in same)
        return depth[nid]

    for nid in by:
        d(nid)
    return bands, depth


# ---------- writing ----------

def build(course, today=None):
    today = today or date.today()
    spec, spath = load_spec(course)
    if not spec:
        return None
    rows = learner_rows(course)
    added = adopt_new_rows(spec, spath, rows)
    by = resolve(spec, rows)
    notes = notes_for(course)

    # level-up memory
    sfile = COURSES / course / ".skilltree.json"
    state = json.loads(sfile.read_text()) if sfile.exists() else {}
    first = not state
    for n in spec["nodes"]:
        st = state.setdefault(n["id"], {})
        prev = st.get("level")
        if prev is not None and n["level"] > prev:
            st["up"] = today.isoformat()
        elif first and n["seen"] and n["level"] >= 2 and (today - date.fromisoformat(n["seen"])).days <= 3:
            st["up"] = n["seen"]                      # first build: recent work counts as fresh
        st["level"] = n["level"]
    sfile.write_text(json.dumps(state, indent=1))

    bands, depth = layout(spec, by)
    nodes, edges = [], []
    known = [n for n in spec["nodes"]]
    frac = progress(known)
    counts = {k: sum(1 for n in known if n["level"] == k) for k in (4, 3, 2, 1, 0, -1)}
    ready = [n for n in known if n["level"] < 0 and n.get("ready")]
    fresh = [n for n in known if state[n["id"]].get("up") and
             today - date.fromisoformat(state[n["id"]]["up"]) <= timedelta(days=7)]
    weak = sorted([n for n in known if n["level"] in (1, 2)], key=lambda n: (n["level"], n["seen"]))

    head = [f"# 🌳 {spec.get('title', course)}", f"*{spec['tagline']}*" if spec.get("tagline") else "",
            f"## {bar(frac)} {round(100 * frac)}%",
            f"⭐ {counts[4]} · 🟩 {counts[3]} · 🟨 {counts[2]} · 🟥 {counts[1]} · ⬜ {counts[0]} · 🔭 {counts[-1]} ahead  "
            f"of **{len(known)}** skills"]
    if fresh:
        head.append("**✨ New progress this week:** " + ", ".join(n["label"] for n in fresh[:5]))
    if weak:
        head.append("**🎯 Strengthen next:** " + ", ".join(n["label"] for n in weak[:3]))
    if ready:
        head.append("**🔓 Ready to learn:** " + ", ".join(n["label"] for n in ready[:3]))
    head.append("\n*⭐ mastered · 🟩 solid · 🟨 developing · 🟥 shaky · ⬜ seen, not yet · 🔓 ready · 🔒 locked. "
                "Arrows: green = that prerequisite is solid (the path is lit), grey = it still needs work. Click a 📝 link to open the note. Updated " + f"{datetime.now():%-m/%-d %-I:%M %p}* · [[Courses/{course}/Learner Model|Learner Model]]")
    head_text = "\n".join(x for x in head if x)
    head_h = est_height(head_text) + 40
    nodes.append({"id": "header", "type": "text", "text": head_text, "x": 0, "y": 0, "width": 760, "height": head_h,
                  "color": spec.get("accent", "6")})

    y = head_h + 80
    pos = {}
    for bi, b in enumerate(bands):
        members = [n for n in spec["nodes"] if n["branch"] == b["id"]]
        by_depth = {}
        for n in members:
            by_depth.setdefault(depth[n["id"]], []).append(n)
        cols, ci = {}, 0                                   # wrap tall columns: at most MAXCOL cards each
        for dpt in sorted(by_depth):
            ns = by_depth[dpt]
            for k in range(0, len(ns), MAXCOL):
                cols[ci] = ns[k:k + MAXCOL]
                ci += 1
        texts = {n["id"]: card_text(n, by, mentions(n, notes), state, today) for n in members}
        col_h = {c: sum(est_height(texts[n["id"]]) for n in ns) + GY * (len(ns) - 1) for c, ns in cols.items()}
        band_h = max(col_h.values()) + 2 * PAD + 30
        band_w = len(cols) * (W + GX) - GX + 2 * PAD
        bf = progress(members)
        label = f"{b['name']}   {bar(bf, 8)} {round(100 * bf)}%"
        nodes.append({"id": f"band-{b['id']}", "type": "group", "label": label, "x": -PAD, "y": y - PAD - 30,
                      "width": band_w, "height": band_h, **({"color": b["color"]} if b.get("color") else {})})
        for c in sorted(cols):
            cy = y
            for n in cols[c]:
                h = est_height(texts[n["id"]])
                lvl = n["level"]
                color = READY if (lvl < 0 and n.get("ready")) else COLOR.get(lvl)
                card = {"id": n["id"], "type": "text", "text": texts[n["id"]], "x": c * (W + GX), "y": cy,
                        "width": W, "height": h}
                if color:
                    card["color"] = color
                nodes.append(card)
                pos[n["id"]] = (bi, c)
                cy += h + GY
        y += band_h + 70

    for n in spec["nodes"]:
        for x in n["needs"]:
            (sb, sc), (tb, tc) = pos[x], pos[n["id"]]
            if sb != tb:
                continue                                  # across units: listed on the card instead (keeps the map clean)
            if sb == tb and sc < tc:
                sides = ("right", "left")
            elif sb < tb:
                sides = ("bottom", "top")
            else:
                sides = ("top", "bottom") if sb > tb else ("right", "left")
            e = {"id": f"{x}->{n['id']}", "fromNode": x, "fromSide": sides[0], "toNode": n["id"], "toSide": sides[1]}
            if by[x]["level"] >= 3:
                e["color"] = "4"                          # a solid prerequisite lights the path
            edges.append(e)

    out = COURSES / course / "Skill Tree.canvas"
    out.write_text(json.dumps({"nodes": nodes, "edges": edges}, indent=1, ensure_ascii=False))
    return {"course": course, "title": spec.get("title", course), "frac": frac, "counts": counts, "n": len(known),
            "ready": ready, "fresh": fresh, "weak": weak, "added": added}


def overview(results):
    out = ["# 🌳 Skill Trees", "",
           "> One map per class, colored by your Learner Models (generated by `tools/skilltree.py`). Click a class to open "
           "its tree; on the tree, every skill links to the notes where you worked on it.", "", "## At a glance", "",
           "| Class | Progress | |", "|---|---|---|"]
    for r in sorted(results, key=lambda r: -r["frac"]):
        fresh = f"✨ {len(r['fresh'])} new" if r["fresh"] else ""
        out.append(f"| [[Courses/{r['course']}/Skill Tree.canvas\\|{r['title']}]] | `{bar(r['frac'], 16)}` "
                   f"**{round(100 * r['frac'])}%** | {fresh} |")
    out += ["", "## Details", ""]
    for r in sorted(results, key=lambda r: -r["frac"]):
        c = r["counts"]
        line = (f"### [[Courses/{r['course']}/Skill Tree.canvas|{r['title']}]]\n"
                f"`{bar(r['frac'], 16)}` **{round(100 * r['frac'])}%** · ⭐ {c[4]} · 🟩 {c[3]} · 🟨 {c[2]} · 🟥 {c[1]} · "
                f"⬜ {c[0]} · 🔭 {c[-1]} ahead")
        extra = []
        if r["fresh"]:
            extra.append("✨ " + ", ".join(n["label"] for n in r["fresh"][:3]))
        if r["weak"]:
            extra.append("🎯 " + ", ".join(n["label"] for n in r["weak"][:2]))
        if r["ready"]:
            extra.append("🔓 " + ", ".join(n["label"] for n in r["ready"][:2]))
        out += [line] + ([" · ".join(extra)] if extra else []) + [""]
    (VAULT / "Skill Trees.md").write_text("\n".join(out))


def main():
    args = sys.argv[1:]
    courses = sorted(p.parent.name for p in COURSES.glob("*/_skilltree.yaml")) if (not args or args == ["--all"]) else args
    results = []
    for c in courses:
        r = build(c)
        if not r:
            print(f"{c}: no _skilltree.yaml")
            continue
        results.append(r)
        msg = f"{c}: {round(100 * r['frac'])}% · {r['n']} skills"
        if r["added"]:
            msg += f" · 🆕 added from the Learner Model (give them a branch + needs in _skilltree.yaml): {', '.join(r['added'])}"
        print(msg)
    # the overview always covers every class, even when one class was rebuilt
    if args and args != ["--all"]:
        done = {r["course"] for r in results}
        for p in sorted(COURSES.glob("*/_skilltree.yaml")):
            if p.parent.name not in done:
                r = build(p.parent.name)
                if r:
                    results.append(r)
    overview(results)


if __name__ == "__main__":
    main()
