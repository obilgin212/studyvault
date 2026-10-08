"""Run code blocks from an Obsidian note the same way the Execute Code plugin does (label/import, pre/post exports).

  notecode.py list <note.md>
  notecode.py run  <note.md> <index|label> [--tests FILE]

Python: `run` prepends `pre` exports and named imports, appends `post` exports, and runs it with tools/runpy.
--tests FILE replaces the block's own `import` with FILE (hidden tests for `check`).
Haskell: delegates to tools/hsnote.py (the note is one ghci session: every Haskell block above is loaded).
--tests FILE appends FILE's `ghci>` lines to the block (hidden tests for `check`).
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
RUNNERS = {"haskell": (TOOLS / "runhs", ".hs"), "hs": (TOOLS / "runhs", ".hs"),
           "python": (TOOLS / "runpy", ".py"), "py": (TOOLS / "runpy", ".py")}
LANG_KEY = {"hs": "haskell", "py": "python"}


def parse_args(first_line):
    """Parse `{label: 'x', import: ['a','b'], pre}` (the plugin uses JSON5; this covers what we write)."""
    if "{" not in first_line:
        return {"export": []}
    body = first_line[first_line.index("{") + 1:first_line.rindex("}")]
    args, exports = {}, []
    for m in re.finditer(r"(\w+)\s*[:=]\s*(\[[^\]]*\]|'[^']*'|\"[^\"]*\"|[\w.-]+)", body):
        key, raw = m.group(1), m.group(2)
        if raw.startswith("["):
            val = re.findall(r"['\"]([^'\"]*)['\"]", raw)
        else:
            val = raw.strip("'\"")
        args[key] = val
    stripped = re.sub(r"(\w+)\s*[:=]\s*(\[[^\]]*\]|'[^']*'|\"[^\"]*\"|[\w.-]+)", "", body)
    exports = re.findall(r"\b(pre|post)\b", stripped)
    ex = args.get("export", [])
    args["export"] = (ex if isinstance(ex, list) else [ex]) + exports
    return args


def blocks(note_text):
    """Top-level fenced code blocks, in order: dicts with lang, args, code, line."""
    out, cur = [], None
    for i, line in enumerate(note_text.split("\n"), 1):
        if line.startswith("```"):
            if cur is None:
                lang = line[3:].strip().split("{")[0].strip().split(" ")[0].lower()
                lang = lang.removeprefix("run-")
                cur = {"lang": LANG_KEY.get(lang, lang), "args": parse_args(line), "code": [], "line": i}
            else:
                cur["code"] = "\n".join(cur["code"]) + "\n"
                out.append(cur)
                cur = None
        elif cur is not None:
            cur["code"].append(line)
    return out


def assemble(bs, idx, tests_file=None):
    target = bs[idx]
    pre, post, named = [], [], {}
    for b in bs[:idx]:
        if b["lang"] != target["lang"]:
            continue
        if "label" in b["args"]:
            named[b["args"]["label"]] = b["code"]
        if "pre" in b["args"]["export"]:
            pre.append(b["code"])
        if "post" in b["args"]["export"]:
            post.append(b["code"])
    imports = target["args"].get("import", [])
    imports = imports if isinstance(imports, list) else [imports]
    if tests_file:
        imported = [Path(tests_file).read_text()]
    else:
        missing = [n for n in imports if n not in named]
        if missing:
            sys.exit(f"import {missing} not found above block {idx} (labels must come *before* the block that imports them)")
        imported = [named[n] for n in imports]
    ignore = target["args"].get("ignore")
    parts = []
    if ignore != "all" and "pre" not in (ignore or []):
        parts += pre
    parts += imported + [target["code"]]
    if ignore != "all" and "post" not in (ignore or []):
        parts += post
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "run"])
    ap.add_argument("note")
    ap.add_argument("which", nargs="?")
    ap.add_argument("--tests")
    a = ap.parse_args()
    bs = blocks(Path(a.note).read_text())

    if a.cmd == "list":
        for i, b in enumerate(bs):
            first = next((l for l in b["code"].splitlines() if l.strip()), "")
            args = {k: v for k, v in b["args"].items() if v}
            print(f"[{i}] line {b['line']} {b['lang']} {args or ''}  {first[:60]}")
        return

    if a.which is None:
        sys.exit("run needs a block index or label")
    if a.which.isdigit():
        idx = int(a.which)
    else:
        idx = next((i for i, b in enumerate(bs) if b["args"].get("label") == a.which), None)
        if idx is None:
            sys.exit(f"no block labelled {a.which!r}")
    lang = bs[idx]["lang"]
    if lang == "haskell":
        hs_index = sum(1 for b in bs[:idx] if b["lang"] == "haskell")
        cmd = [sys.executable, str(TOOLS / "hsnote.py"), "--note", a.note, "--block", str(hs_index)]
        if a.tests:
            cmd += ["--extra", a.tests]
        sys.exit(subprocess.run(cmd).returncode)
    if lang not in RUNNERS:
        sys.exit(f"can't run {lang!r} blocks")
    runner, ext = RUNNERS[lang]
    src = assemble(bs, idx, a.tests)
    with tempfile.NamedTemporaryFile("w", suffix=ext, delete=False) as f:
        f.write(src)
    # Off-screen plotting: Obsidian captures plt.show() itself, but here it would open a window and hang.
    env = {**os.environ, "MPLBACKEND": "Agg"}
    r = subprocess.run([str(runner), f.name], capture_output=True, text=True, timeout=60, env=env)
    print(r.stdout, end="")
    if r.stderr.strip():
        print("--- stderr ---\n" + r.stderr.replace(f.name, "<block>"), end="")
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
