"""Test intelligence: learn how a teacher writes tests from past tests/quizzes/practice tests, so practice matches.

  ~/miniconda3/envs/study/bin/python tools/testprofile.py add "<course>" <record.json>     add/replace one assessment
  ~/miniconda3/envs/study/bin/python tools/testprofile.py build "<course>"                 rebuild Test Profile.md + stats
  ~/miniconda3/envs/study/bin/python tools/testprofile.py forecast "<course>" <forecast.json>  log a prediction
  ~/miniconda3/envs/study/bin/python tools/testprofile.py score "<course>" "<test id>"     score the forecast vs. the real test
  ~/miniconda3/envs/study/bin/python tools/testprofile.py list "<course>"

Data: Courses/<course>/Tests/tests.json (every question of every assessment, tagged). Outputs:
  Tests/Test Profile.md   the teacher's pattern: structure, topic weights, recurring archetypes + twists, sources,
                          {{NAME}}'s results per pattern, forecast accuracy, and a "how to practice" recipe
  Tests/stats.json        per-skill-node test weight + misses (read by tools/skilltree.py)

The more assessments are added, the better it gets: every number is a weighted average over all of them
(real tests count most, quizzes less, practice tests/homework least; recent ones count more), each pattern
shows how many assessments support it, and forecasts are scored against what the real test had.

record.json (one assessment):
{"id": "2026-10-08 Ch4 Test", "date": "2026-10-08", "kind": "test|quiz|practice|homework", "chapter": "4",
 "title": "Chapter 4 Test", "files": ["_sources/tests/ch4-test.pdf"], "minutes": 50, "total_points": 60,
 "score": 51, "made_by": "teacher|textbook|ap",
 "questions": [{"n": "3", "format": "mc|frq|short|proof|other", "points": 2, "calc": false, "parts": 1,
                "skills": ["invslope"], "archetype": "inverse-slope-solve-for-b",
                "twists": ["no-scaffold", "solve-hidden-step"], "source": "§4.3 #28 (unscaffolded)",
                "difficulty": 3, "result": "right|wrong|partial|blank|unknown", "lost": "used f'(a)"}]}
Archetypes are chapter-specific problem types; twists are the teacher's moves that carry over to new chapters.
"""
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

VAULT = Path(__file__).resolve().parent.parent
KIND_WEIGHT = {"test": 1.0, "quiz": 0.7, "practice": 0.5, "homework": 0.25}
HALF_LIFE = 4                       # an assessment 4 places older counts half as much
FORMATS = ["mc", "frq", "short", "proof", "other"]

# shared twist vocabulary: the teacher's habits, which transfer to any chapter (extend freely, keep the ids stable)
TWISTS = {
    "no-scaffold": "Asks the end question directly; the book's helper parts (a), (b) are removed",
    "solve-hidden-step": "A hidden step must be solved first (find the input, the point, the constant)",
    "multi-rep": "Information given as a table, graph or words instead of a formula",
    "reverse": "Runs a familiar problem backwards (given the answer/derivative, find the original)",
    "prior-chapter": "Needs a skill from an earlier chapter inside a new-chapter problem",
    "messy-algebra": "Correct method, but the algebra/simplification is long or error-prone",
    "justify": "Asks for a written justification (name the theorem, state why), graded on wording",
    "trap-distractor": "MC distractors built from a specific common mistake",
    "no-calc-numbers": "No calculator, so the numbers are chosen to come out nice (integer roots, known angles)",
    "combined-skills": "Two or more skills from this chapter chained in one problem",
    "conceptual": "Asks what/why rather than compute (true/false, which must be true, explain)",
    "unit-context": "Applied context with units (rates, motion, money) that must be interpreted",
    "long-multi-part": "One stem with 3+ dependent parts; an early mistake carries forward",
}


def tests_dir(course):
    return VAULT / "Courses" / course / "Tests"


def load(course):
    p = tests_dir(course) / "tests.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"tests": [], "archetypes": {}, "forecasts": []}


def save(course, db):
    d = tests_dir(course)
    d.mkdir(parents=True, exist_ok=True)
    (d / "tests.json").write_text(json.dumps(db, indent=1, ensure_ascii=False), encoding="utf-8")


def spec_nodes(course):
    p = VAULT / "Courses" / course / "_skilltree.yaml"
    if not p.exists():
        return {}, {}
    spec = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    branches = {b["id"]: b["name"] for b in spec.get("branches", [])}
    return {n["id"]: n for n in spec.get("nodes", [])}, branches


def validate(rec, nodes):
    errs = []
    for k in ("id", "date", "kind", "questions"):
        if k not in rec:
            errs.append(f"missing {k}")
    if rec.get("kind") not in KIND_WEIGHT:
        errs.append(f"kind must be one of {list(KIND_WEIGHT)}")
    for q in rec.get("questions", []):
        if q.get("format") not in FORMATS:
            errs.append(f"q{q.get('n')}: format must be one of {FORMATS}")
        for s in q.get("skills", []):
            if nodes and s not in nodes:
                errs.append(f"q{q.get('n')}: skill '{s}' is not a node id in _skilltree.yaml")
        for t in q.get("twists", []):
            if t not in TWISTS:
                errs.append(f"q{q.get('n')}: unknown twist '{t}' (add it to TWISTS in tools/testprofile.py if it's new)")
        if q.get("result", "unknown") not in ("right", "wrong", "partial", "blank", "unknown"):
            errs.append(f"q{q.get('n')}: result must be right|wrong|partial|blank|unknown")
    return errs


# ---------- statistics ----------

def weights(tests):
    """Kind weight × recency (half-life HALF_LIFE assessments, newest = 1)."""
    order = sorted(tests, key=lambda t: t["date"], reverse=True)
    rank = {t["id"]: i for i, t in enumerate(order)}
    return {t["id"]: KIND_WEIGHT[t["kind"]] * 0.5 ** (rank[t["id"]] / HALF_LIFE) for t in tests}


def missed(q):
    return {"wrong": 1.0, "blank": 1.0, "partial": 0.5}.get(q.get("result"), 0.0)


def stats(db, nodes):
    tests = db["tests"]
    w = weights(tests)
    s = {"n_tests": len(tests), "by_kind": defaultdict(int), "structure": {}, "skills": defaultdict(lambda: [0.0, 0, 0.0]),
         "archetypes": defaultdict(lambda: {"w": 0.0, "n": 0, "miss": 0.0, "seen": []}),
         "twists": defaultdict(lambda: {"w": 0.0, "n": 0, "miss": 0.0, "tests": set()}),
         "sources": defaultdict(float), "formats_miss": defaultdict(lambda: [0, 0.0])}
    for t in tests:
        s["by_kind"][t["kind"]] += 1
    # structure: per kind, weighted mean of counts/points/time
    for kind in KIND_WEIGHT:
        ts = [t for t in tests if t["kind"] == kind]
        if not ts:
            continue
        tw = sum(w[t["id"]] for t in ts)
        def avg(f):
            return sum(w[t["id"]] * f(t) for t in ts) / tw
        st = {"n": len(ts), "questions": avg(lambda t: len(t["questions"]))}
        for fmt in FORMATS:
            st[fmt] = avg(lambda t, fmt=fmt: sum(1 for q in t["questions"] if q.get("format") == fmt))
        st["minutes"] = [t.get("minutes") for t in ts if t.get("minutes")]
        st["points"] = [t.get("total_points") for t in ts if t.get("total_points")]
        st["calc_share"] = avg(lambda t: sum(1 for q in t["questions"] if q.get("calc")) / max(1, len(t["questions"])))
        st["hard_share"] = avg(lambda t: sum(1 for q in t["questions"] if (q.get("difficulty") or 0) >= 3) / max(1, len(t["questions"])))
        st["multipart"] = avg(lambda t: sum(1 for q in t["questions"] if (q.get("parts") or 1) >= 3))
        s["structure"][kind] = st
    # skills, archetypes, twists, sources, format misses
    for t in tests:
        wt = w[t["id"]]
        for q in t["questions"]:
            m = missed(q)
            share = wt / max(1, len(q.get("skills", [])))
            for sk in q.get("skills", []):
                rec = s["skills"][sk]
                rec[0] += share
                rec[1] += 1
                rec[2] += m
            a = q.get("archetype")
            if a:
                ar = s["archetypes"][a]
                ar["w"] += wt
                ar["n"] += 1
                ar["miss"] += m
                ar["seen"].append(f"{t['id']} #{q.get('n')}")
            for tw_ in q.get("twists", []):
                tr = s["twists"][tw_]
                tr["w"] += wt
                tr["n"] += 1
                tr["miss"] += m
                tr["tests"].add(t["id"])
            src = (q.get("source") or "").lower()
            kind = ("textbook" if re.search(r"§|\bex\b|exercise|review|#\d", src) else
                    "AP released" if "ap" in src.split() or "released" in src else
                    "unknown" if not src else "other")
            s["sources"][kind] += wt
            fm = s["formats_miss"][q.get("format", "other")]
            fm[0] += 1
            fm[1] += m
    return s


def confidence(n):
    return "low (1 assessment: patterns are guesses)" if n <= 1 else \
           "medium (2–3 assessments)" if n <= 3 else "high (4+ assessments)"


def pct(x):
    return f"{round(100 * x)}%"


def render(course, db, s, nodes, branches):
    tests = sorted(db["tests"], key=lambda t: t["date"])
    total_w = sum(weights(db["tests"]).values()) or 1
    L = [f"<!-- generated by tools/testprofile.py build: edit Tests/tests.json or the notes below the END marker, not this part -->",
         f"# 🎯 {course}: Test Profile", "",
         f"> How this teacher writes tests, learned from **{s['n_tests']}** assessment(s): "
         + ", ".join(f"{n} {k}{'s' if n > 1 else ''}" for k, n in s["by_kind"].items())
         + f". Confidence: **{confidence(s['by_kind'].get('test', 0) + s['by_kind'].get('quiz', 0))}**. "
         "Real tests count most, then quizzes, then practice tests and homework; recent ones count more. "
         "Add more with `/past-tests add`: every new one sharpens this.", ""]
    L += ["## 🗂️ Assessments learned from", "| Date | Assessment | Kind | Qs | Score | Missed / partial |", "|---|---|---|---|---|---|"]
    for t in tests:
        miss = [q.get("n") for q in t["questions"] if q.get("result") in ("wrong", "blank", "partial")]
        sc = f"{t['score']}/{t['total_points']}" if t.get("score") is not None and t.get("total_points") else "—"
        note = f"[[Courses/{course}/Tests/{t['id']}|{t.get('title') or t['id']}]]" if (tests_dir(course) / f"{t['id']}.md").exists() else (t.get("title") or t["id"])
        L.append(f"| {t['date']} | {note} | {t['kind']} | {len(t['questions'])} | {sc} | {', '.join(map(str, miss)) or '—'} |")
    # structure
    L += ["", "## 🧱 Structure (what a typical one looks like)"]
    for kind, st in s["structure"].items():
        fm = " · ".join(f"{st[f]:.1f} {f.upper()}" for f in FORMATS if st[f] >= 0.05)
        mins = f"{round(sum(st['minutes']) / len(st['minutes']))} min" if st["minutes"] else "time ?"
        pts = f"{round(sum(st['points']) / len(st['points']))} pts" if st["points"] else "points ?"
        L.append(f"- **{kind.title()}** (from {st['n']}): ~{st['questions']:.0f} questions = {fm} · {mins} · {pts} · "
                 f"calculator on {pct(st['calc_share'])} · hard (3/3) {pct(st['hard_share'])} · "
                 f"{st['multipart']:.1f} long multi-part")
    # topic weights by unit
    by_branch = defaultdict(float)
    for sk, (wsum, n, m) in s["skills"].items():
        b = branches.get(nodes.get(sk, {}).get("branch"), "other")
        by_branch[b] += wsum
    tot = sum(by_branch.values()) or 1
    L += ["", "## 📚 Where the points go (by unit)"]
    L += [f"- {b}: **{pct(v / tot)}**" for b, v in sorted(by_branch.items(), key=lambda x: -x[1])]
    # skills
    L += ["", "## 🧩 Most-tested skills", "| Skill | Questions | Missed | Per test (weighted) |", "|---|---|---|---|"]
    for sk, (wsum, n, m) in sorted(s["skills"].items(), key=lambda x: -x[1][0])[:15]:
        label = nodes.get(sk, {}).get("label", sk)
        L.append(f"| {label} | {n} | {m:g} | {wsum / total_w:.2f} |")
    # twists
    L += ["", "## 🌀 The teacher's moves (twists: these carry over to new chapters)",
          "| Move | How often | In how many assessments | Your miss rate |", "|---|---|---|---|"]
    n_ass = max(1, s["n_tests"])
    for tw_, r in sorted(s["twists"].items(), key=lambda x: -x[1]["w"]):
        L.append(f"| **{tw_}**: {TWISTS.get(tw_, '')} | {r['n']} question(s) | {len(r['tests'])}/{n_ass} | "
                 f"{pct(r['miss'] / r['n']) if r['n'] else '—'} |")
    # archetypes
    arch_info = db.get("archetypes", {})
    L += ["", "## 🧗 Recurring problem types (archetypes)", "| Archetype | Times | Missed | Seen in |", "|---|---|---|---|"]
    for a, r in sorted(s["archetypes"].items(), key=lambda x: (-x[1]["w"], x[0])):
        lab = arch_info.get(a, {}).get("label", a)
        L.append(f"| **{lab}** | {r['n']} | {r['miss']:g} | {', '.join(r['seen'][-3:])} |")
    # sources
    st = sum(s["sources"].values()) or 1
    L += ["", "## 📖 Where questions come from", " · ".join(f"{k}: {pct(v / st)}" for k, v in sorted(s["sources"].items(), key=lambda x: -x[1]))]
    # formats
    L += ["", "## 📝 Your results by format", " · ".join(f"{f.upper()}: missed {m:g} of {n}" for f, (n, m) in s["formats_miss"].items())]
    # forecasts
    fc = [f for f in db.get("forecasts", []) if f.get("score")]
    if fc:
        L += ["", "## 🔮 How good the forecasts have been", "| Forecast for | Twists hit | Skills hit | Structure |", "|---|---|---|---|"]
        for f in fc:
            sc = f["score"]
            L.append(f"| {f['for']} | {pct(sc['twists'])} | {pct(sc['skills'])} | {sc['structure']} |")
    # practice recipe
    # a "habit": in every assessment so far (1–2 of them), or in at least two-thirds once there are 3+
    common = [t for t, r in sorted(s["twists"].items(), key=lambda x: -x[1]["w"])
              if (len(r["tests"]) == n_ass if n_ass <= 2 else len(r["tests"]) / n_ass >= 2 / 3)]
    risky = sorted(((t, r["miss"] / r["n"]) for t, r in s["twists"].items() if r["n"]), key=lambda x: -x[1])
    typ = s["structure"].get("test") or s["structure"].get("quiz") or next(iter(s["structure"].values()), None)
    L += ["", "## 🏋️ How to practice for this teacher (auto)"]
    if typ:
        L.append(f"- **Mock tests copy the structure:** ~{typ['questions']:.0f} questions, "
                 + " · ".join(f"{typ[f]:.0f} {f.upper()}" for f in FORMATS if typ[f] >= 0.5)
                 + (f", {round(sum(typ['minutes']) / len(typ['minutes']))} min" if typ["minutes"] else "")
                 + f", ~{pct(typ['hard_share'])} hard.")
    if common:
        L.append("- **Every mock must include these moves** (they show up on most assessments): " + ", ".join(f"`{c}`" for c in common))
    if risky and risky[0][1] > 0:
        L.append("- **Extra reps on the moves that cost you points:** " + ", ".join(f"`{t}` ({pct(m)} missed)" for t, m in risky[:3] if m > 0))
    L.append("- **New chapter?** Re-use the moves, not the old content: apply each common move to the new chapter's skills "
             "(e.g. `solve-hidden-step` in a new chapter = whatever input or point must be found before the main rule applies).")
    L += ["", "<!-- END generated -->"]
    return "\n".join(L)


def build(course):
    db = load(course)
    nodes, branches = spec_nodes(course)
    s = stats(db, nodes)
    d = tests_dir(course)
    d.mkdir(parents=True, exist_ok=True)
    prof = d / "Test Profile.md"
    keep = ""
    if prof.exists():
        old = prof.read_text(encoding="utf-8")
        if "<!-- END generated -->" in old:
            keep = old.split("<!-- END generated -->", 1)[1]
    if not keep.strip():
        keep = ("\n\n## ✍️ Tutor's notes (kept across rebuilds)\n*Qualitative patterns the numbers can't show "
                "(wording habits, how partial credit is given, what the teacher said in class about the test).*\n")
    prof.write_text(render(course, db, s, nodes, branches) + keep, encoding="utf-8")
    total_w = sum(weights(db["tests"]).values()) or 1
    st = {sk: {"weight": round(wsum / total_w, 3), "n": n, "missed": m} for sk, (wsum, n, m) in s["skills"].items()}
    (d / "stats.json").write_text(json.dumps(st, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{course}: {s['n_tests']} assessment(s), {sum(len(t['questions']) for t in db['tests'])} questions → "
          f"Tests/Test Profile.md, Tests/stats.json")


def score(course, test_id):
    """Compare the logged forecast for test_id with the real test's twists, skills and structure."""
    db = load(course)
    real = next((t for t in db["tests"] if t["id"] == test_id), None)
    fc = next((f for f in db.get("forecasts", []) if f.get("for") == test_id), None)
    if not real or not fc:
        sys.exit("need both the real test (add) and a logged forecast with \"for\": that test id")
    rt = {t for q in real["questions"] for t in q.get("twists", [])}
    rs = {s for q in real["questions"] for s in q.get("skills", [])}
    ft, fs = set(fc.get("twists", [])), set(fc.get("skills", []))
    tw = len(rt & ft) / len(rt) if rt else 1.0
    sk = len(rs & fs) / len(rs) if rs else 1.0
    fq = fc.get("structure", {}).get("questions")
    struct = f"predicted {fq} questions, real {len(real['questions'])}" if fq else "—"
    fc["score"] = {"twists": tw, "skills": sk, "structure": struct, "missed_twists": sorted(rt - ft),
                   "missed_skills": sorted(rs - fs), "scored": date.today().isoformat()}
    save(course, db)
    print(json.dumps(fc["score"], indent=1, ensure_ascii=False))


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, course = sys.argv[1], sys.argv[2]
    if not (VAULT / "Courses" / course).exists():
        sys.exit(f"no course folder: Courses/{course}")
    db = load(course)
    nodes, _ = spec_nodes(course)
    if cmd == "add":
        rec = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        errs = validate(rec, nodes)
        if errs:
            sys.exit("not added:\n  " + "\n  ".join(errs))
        for a, info in (rec.pop("archetypes", None) or {}).items():      # optional {"id": {"label", "transfer"}}
            db["archetypes"].setdefault(a, {}).update(info)
        db["tests"] = [t for t in db["tests"] if t["id"] != rec["id"]] + [rec]
        save(course, db)
        print(f"added {rec['id']} ({len(rec['questions'])} questions)")
        build(course)
    elif cmd == "build":
        build(course)
    elif cmd == "forecast":
        fc = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        fc.setdefault("made", date.today().isoformat())
        db["forecasts"] = [f for f in db.get("forecasts", []) if f.get("for") != fc.get("for")] + [fc]
        save(course, db)
        print(f"forecast logged for {fc.get('for')}")
    elif cmd == "score":
        score(course, sys.argv[3])
        build(course)
    elif cmd == "list":
        for t in sorted(db["tests"], key=lambda t: t["date"]):
            print(f"{t['date']}  {t['kind']:9} {t['id']}  ({len(t['questions'])} q)")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
