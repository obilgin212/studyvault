"""Notebook-style Haskell for Obsidian notes: write code like Python; the note is one session, read top to bottom.

Running a Haskell block:
  * every Haskell block above it (and the block itself) is loaded; a later definition of a name replaces earlier ones;
  * each top-level item (a line at column 0 + its indented continuation) is classified automatically:
    definitions (`f x = ...`, guards, signatures, data/type/class/instance/import, `x = ...`, `let x = ...`) are loaded,
    everything else is an expression and is evaluated, output shown (several get a `▸` label);
    something that looks like a definition but fails to parse is retried as an expression;
  * `:t` / `:i` / `:k` lines are passed to ghci; `:l path.hs` loads a file's definitions (relative to note, then vault);
  * legacy `ghci> ...` lines still work;
  * a block with only definitions prints "✓ Loaded: ..." (or runs `main` if it defines one);
  * blocks above that don't compile are skipped with a warning.

Invoked two ways:
  plugin:   hsnote.py [-f ghc] <tmpfile.hs>   (tmpfile's first line is `-- HSNOTE "<vault>" "<note>"`, via haskellInject)
  terminal: hsnote.py --note <note.md> --block <n> [--extra FILE]   (n = index among the note's Haskell blocks;
            --extra appends FILE's lines (e.g. `runTests [...]`) to that block, e.g. hidden tests for `check`)
"""
import argparse
import difflib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HOME = Path.home()
GHCI = HOME / ".ghcup/bin/ghci"
CHECK_DIR = Path(__file__).resolve().parent / "hs"
PROMPT = "ghci>"
HEADER = re.compile(r'^--\s*HSNOTE\s+"([^"]*)"\s+"([^"]*)"\s*$')
OPCHARS = r"[!#$%&*+./<=>?@\\^|~:-]+"


# ---------- reading the note ----------

def haskell_blocks(text):
    """Top-level ```haskell / ```hs blocks: list of code strings (fence args ignored)."""
    out, cur = [], None
    for line in text.split("\n"):
        if line.startswith("```"):
            if cur is None:
                lang = line[3:].strip().split("{")[0].strip().split(" ")[0].lower().removeprefix("run-")
                cur = [] if lang in ("haskell", "hs") else False
            else:
                if cur is not False:
                    out.append("\n".join(cur))
                cur = None
        elif cur not in (None, False):
            cur.append(line)
    return out


DEF_KEYWORDS = ("data ", "type ", "newtype ", "class ", "instance ", "deriving ", "import ",
                "infixl ", "infixr ", "infix ", "{-#", "module ")
EXPR_KEYWORDS = ("do", "if", "case", "\\", "let")


def depth0_tokens(line):
    """Yield (index, token) for `=` and `::` that sit outside brackets/strings and aren't part of ==, >=, =>, ..."""
    depth, i, n = 0, 0, len(line)
    in_str = None
    while i < n:
        ch = line[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
        elif ch == '"':
            in_str = '"'
        elif ch == "'" and i + 2 < n and line[i + 2] == "'":   # char literal like 'a'
            i += 3
            continue
        elif ch == "-" and line[i:i + 2] == "--":
            break
        elif depth == 0 and line.startswith("where", i) and (i == 0 or not (line[i - 1].isalnum() or line[i - 1] in "_'")) \
                and (i + 5 >= n or not (line[i + 5].isalnum() or line[i + 5] in "_'")):
            break
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif depth == 0 and ch in "=:":
            j = i
            while j < n and line[j] in OPCHARS_SET:
                j += 1
            k = i
            while k > 0 and line[k - 1] in OPCHARS_SET:
                k -= 1
            tok = line[k:j]
            if tok in ("=", "::"):
                yield k, tok
            i = j
            continue
        i += 1


OPCHARS_SET = set("!#$%&*+./<=>?@\\^|~:-")


def is_definition(glines):
    first = glines[0].strip()
    if first.startswith(DEF_KEYWORDS):
        return True
    if first.startswith("let "):
        return not re.search(r"\bin\b", "\n".join(glines))
    word = re.match(r"[\w']+|\S", first).group(0)
    if word in EXPR_KEYWORDS:
        return False
    toks = list(depth0_tokens(first))
    if toks:
        idx, tok = toks[0]
        if tok == "=":
            return True
        # `f :: T` / `f, g :: T` / `(+++) :: T` is a signature; `read "5" :: Int` is an annotated expression
        return bool(re.fullmatch(r"\s*(\(" + OPCHARS + r"\)|[a-z_][\w']*)(\s*,\s*[a-z_][\w']*)*\s*", first[:idx]))
    # guards / `=` on a continuation line: f x\n  | x > 0 = ...  (only when line 1 looks like a function head)
    if not re.match(r"^(\(" + OPCHARS + r"\)|[a-z_][\w']*)(\s|$)", first):
        return False
    return any(l.strip().startswith(("|", "=")) and not l.strip().startswith(("||", "==")) for l in glines[1:])


def split_block(code, force_expr=frozenset()):
    """-> (definition groups [(start, lines)], commands [text]).
    A group is a line at column 0 plus its indented continuation lines. Groups that are definitions are loaded;
    everything else (expressions, `:t ...`, legacy `ghci> ...`) is evaluated like ghci would."""
    lines = code.split("\n")
    groups = []   # [start, [lines]]
    for i, ln in enumerate(lines):
        s_ = ln.strip()
        starts = ln[:1] not in (" ", "\t") and s_ and not s_.startswith(("--", "{-")) and not re.match(r"^[,)\]}|]", s_)
        if starts or not groups:
            groups.append([i, [ln]])
        else:
            groups[-1][1].append(ln)
    defs, cmds = [], []
    for start, g in groups:
        while g and not g[-1].strip():
            g.pop()
        if not g:                             # only blank lines (the plugin adds some before the code)
            continue
        body = [l for l in g if l.strip() and not l.strip().startswith("--")]
        if not body:
            defs.append((start, g))           # comments/blank: harmless
            continue
        first = body[0].strip()
        if first.startswith(PROMPT):          # legacy `ghci> expr` / `ghci> let x = ...`
            text = [first[len(PROMPT):].strip()] + [l for l in g[1:] if l.strip()]
            if text[0].startswith("let ") and not re.search(r"\bin\b", "\n".join(text)):
                defs.append((start, [text[0][4:]] + text[1:]))
            elif not text[0].startswith(":") and is_definition(text):
                defs.append((start, text))
            else:
                cmds.append("\n".join(text))
        elif first.startswith(":"):
            cmds.append(first)
        elif start not in force_expr and is_definition(body):
            defs.append((start, g))
        else:
            cmds.append("\n".join(l for l in g if l.strip()))
    return defs, cmds


# ---------- declarations and shadowing ----------

def decl_groups(lines):
    """Group definition lines into top-level declarations: list of (name or None, [lines], kind)."""
    groups = []
    for ln in lines:
        stripped = ln.strip()
        top = ln[:1] not in (" ", "\t") and stripped != ""
        if top and not stripped.startswith("--") and not stripped.startswith("{-"):
            groups.append([decl_name(stripped), [ln], decl_kind(stripped)])
        elif groups:
            groups[-1][1].append(ln)
        else:
            groups.append([None, [ln], "other"])
    return groups


def decl_kind(s):
    if s.startswith("import "):
        return "import"
    if s.startswith("{-#"):
        return "pragma"
    if re.match(r"module\s", s):
        return "module"
    return "decl"


def decl_name(s):
    m = re.match(r"(data|newtype|type|class)\s+(?:.*=>\s*)?([A-Z][\w']*)", s)
    if m:
        return "type:" + m.group(2)
    if s.startswith(("instance ", "import ", "{-#", "module ", "deriving ")):
        return None
    m = re.match(r"^\(?(" + OPCHARS + r")\)?\s*::", s)           # (+++) :: ...
    if m:
        return m.group(1)
    m = re.match(r"^([a-z_][\w']*)\s*(,\s*[a-z_][\w']*\s*)*::", s)  # f :: ... / f, g :: ...
    if m:
        return m.group(1)
    m = re.match(r"^\S+\s+`([a-z_][\w']*)`\s", s)                  # x `op` y = ...
    if m:
        return m.group(1)
    m = re.match(r"^[\w'\[\]()]+\s+(" + OPCHARS + r")\s", s)       # a +++ b = ...
    if m and m.group(1) not in ("=", "|", "::", "<-", "->"):
        return m.group(1)
    m = re.match(r"^([a-z_][\w']*)\b", s)                          # f x y = ... / x = ...
    if m and m.group(1) not in ("let", "where", "in", "case", "if", "do", "deriving"):
        return m.group(1)
    return None


# ---------- :load ----------

def load_file(arg, note_dir, vault):
    p = arg.strip().strip('"')
    for base in (note_dir, vault):
        f = (base / p) if not os.path.isabs(p) else Path(p)
        if f.suffix == "":
            f = f.with_suffix(".hs")
        if f.exists():
            return f.read_text().split("\n"), f
    return None, p


# ---------- assembling the module ----------

def assemble(blocks, cur, note_dir, vault, skip=frozenset(), force_expr=frozenset()):
    """Build NoteDefs.hs from blocks[0..cur]. Returns (source, line_map, current_cmds, current_names, notes)."""
    pragmas, imports, units = [], [], []   # units: (block_no, [(line, src_line_no)]) per declaration group
    notes = []
    cur_cmds, cur_names = [], []
    for bno, code in enumerate(blocks[:cur + 1]):
        def_groups, cmds = split_block(code, force_expr if bno == cur else frozenset())
        loaded = []
        # ghci> :l file / ghci> let x = ... in blocks count as definitions too
        extra_defs = []
        for c in cmds:
            m = re.match(r"^:(?:l|load)\s+(.+)$", c.strip())
            if m:
                lines, f = load_file(m.group(1), note_dir, vault)
                if lines is None:
                    if bno == cur:
                        notes.append(f"⚠️ :load couldn't find {f}")
                else:
                    loaded.append((lines, f))
        if bno == cur:
            cur_cmds = [c for c in cmds if not re.match(r"^:(?:l|load|r|reload)\b", c.strip())]
        own = [(decl_name(g[0].strip()) if g[0].strip() else None, g,
                decl_kind(g[0].strip()) if g[0][:1] not in (" ", "\t") and g[0].strip()
                and not g[0].strip().startswith(("--", "{-")) else "other", start) for start, g in def_groups]
        sources = [(own, f"block {bno + 1}")] \
            + [([(n, gl, k, gi) for gi, (n, gl, k) in enumerate(decl_groups(ls))], f.name) for ls, f in loaded] \
            + [([(n, gl, k, gi) for gi, (n, gl, k) in enumerate(decl_groups(extra_defs))], f"block {bno + 1}")]
        for si, (groups_, origin) in enumerate(sources):
            for name, glines, kind, gi in groups_:
                if kind == "decl" and name is None and glines and glines[0].strip().startswith("let "):
                    glines = [glines[0].replace("let ", "", 1)] + glines[1:]
                    name = decl_name(glines[0].strip())
                key = (bno, si, gi)
                if key in skip:
                    continue
                if kind == "pragma":
                    pragmas += glines
                elif kind == "import":
                    imports += [l for l in glines if l.strip()]
                elif kind == "module":
                    continue
                else:
                    if name and kind == "decl":
                        before = len(units)
                        units = [u for u in units if u[0] != name or u[3] == (bno, origin)]
                        if len(units) < before and bno == cur:
                            notes.append(f"↻ {name.removeprefix('type:')} replaces an earlier definition")
                        if bno == cur and name not in cur_names and not name.startswith("type:"):
                            cur_names.append(name)
                    units.append((name, glines, origin, (bno, origin), key))

    uses_check = any("runTests" in c or re.search(r"\btest\s+\"", c) for c in cur_cmds)
    # ghci turns these on; without them `let ys = [5,6]` defaults to [Integer] and surprises you
    ghci_like = ["{-# LANGUAGE NoMonomorphismRestriction #-}", "{-# LANGUAGE ExtendedDefaultRules #-}"]
    header = ghci_like + pragmas + ["module NoteDefs where"] + sorted(set(imports), key=imports.index)
    if uses_check and not any(re.match(r"import\s+Check\b", i) for i in imports):
        header.append("import Check")
    src, line_map = list(header), {}
    for name, glines, origin, _, key in units:
        for l in glines:
            src.append(l)
            line_map[len(src)] = (origin, name, key)
    return "\n".join(src) + "\n", line_map, cur_cmds, cur_names, notes


# ---------- running ghci ----------

def tidy_error(text, line_map):
    """Rewrite `NoteDefs.hs:12:5: error:` into `block 3: error:` and drop noise."""
    out = []
    for l in text.split("\n"):
        m = re.match(r"^.*NoteDefs\.hs:(\d+):(\d+)(?:-\d+)?:\s*(.*)$", l)
        if m:
            where = line_map.get(int(m.group(1)))
            loc = f"Haskell {where[0]}" + (f" (in `{where[1].removeprefix('type:')}`)" if where[1] else "") \
                if where else "note"
            out.append(f"{loc}: {m.group(3)}")
            continue
        m = re.match(r"^<interactive>:\d+:\d+(?:-\d+)?:\s*(.*)$", l)
        if m:
            out.append(m.group(1))
            continue
        if re.match(r"^\s*\|", l) or re.match(r"^\s*\d+\s*\|", l):
            continue  # GHC's source-excerpt gutter points into the combined file; skip it
        out.append(l)
    return "\n".join(x for x in out).strip()


def ghci_env():
    return {**os.environ, "PATH": f"{HOME}/.ghcup/bin:{os.environ.get('PATH', '/usr/bin:/bin')}"}


def ghci_session(src, cmds):
    """Load src as NoteDefs.hs, run cmds; returns combined output (None on timeout)."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "NoteDefs.hs").write_text(src)
        (Path(tmp) / "init.ghci").write_text(':set prompt ""\n:set prompt-cont ""\n')
        script = ['putStrLn "<<<HSNOTE-LOADED>>>"']
        for k, c in enumerate(cmds):
            script.append(f'putStrLn "<<<HSNOTE-{k}>>>"')
            script += [":{", c, ":}"] if "\n" in c else [c]
        script.append('putStrLn "<<<HSNOTE-END>>>"')
        try:
            r = subprocess.run([str(GHCI), "-v0", "-w", "-ignore-dot-ghci", "-ghci-script", "init.ghci",
                                f"-i{CHECK_DIR}", "NoteDefs.hs"], input="\n".join(script) + "\n",
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=tmp,
                               timeout=30, env=ghci_env())
        except subprocess.TimeoutExpired:
            return None
    return r.stdout


def run(blocks, cur, note_dir, vault, current_code=None):
    if current_code is not None:
        blocks = blocks[:cur] + [current_code]
    skip, skipped, force_expr = set(), [], set()
    for _ in range(10):
        src, line_map, cmds, names, notes = assemble(blocks, cur, note_dir, vault, frozenset(skip), frozenset(force_expr))
        echo = True
        if not cmds and "main" in names:
            cmds, echo = ["main"], False
        out = ghci_session(src, cmds)
        if out is None:
            print("⏱️ Timed out after 30 s: is something looping forever (e.g. printing an infinite list)?")
            return 1
        load_part = out.partition("<<<HSNOTE-LOADED>>>")[0]
        errs = [(int(m.group(1)), load_part[m.end():m.end() + 300])
                for m in re.finditer(r"NoteDefs\.hs:(\d+):\d+(?:-\d+)?:\s*error", load_part)]
        if not errs:
            break
        # something in *this* block that looked like a definition but doesn't parse as one: evaluate it instead
        flip = set()
        for l, msg in errs:
            if not re.search(r"[Pp]arse error|Invalid type signature", msg):
                continue
            owner = max((k for k in line_map if k <= l), default=None)   # the unit this line is in (or ends before)
            if owner is not None and line_map[owner][2][0] == cur and line_map[owner][2][1] == 0:
                flip.add(line_map[owner][2][2])
        if flip - force_expr:
            force_expr |= flip
            continue
        # a block *above* doesn't compile: skip it (like a bad definition typed into ghci) and carry on
        bad = {line_map[l][2] for l, _ in errs if l in line_map and line_map[l][2][0] != cur} - skip
        if not bad:
            break
        for k in bad:
            ln = next(l for l, v in line_map.items() if v[2] == k)
            skipped.append(f"⚠️ skipped `{(line_map[ln][1] or '?').removeprefix('type:')}` from Haskell {line_map[ln][0]}: it doesn't compile")
        skip |= bad
    load_part, _, rest = out.partition("<<<HSNOTE-LOADED>>>")
    for n in dict.fromkeys(skipped + notes):
        print(n)
    if re.search(r"\berror:", load_part):
        print("❌ Didn't load:\n")
        print(tidy_error(load_part, line_map))
        return 1
    if not cmds:
        print("✓ Loaded" + (": " + ", ".join(n for n in names) if names else " (no new definitions)"))
        return 0
    rest = rest.split("<<<HSNOTE-END>>>")[0]
    parts = re.split(r"<<<HSNOTE-(\d+)>>>\n?", rest)
    results = {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}
    label = echo and len(cmds) > 1
    for k, c in enumerate(cmds):
        res = results.get(k, "").rstrip("\n")
        if label:
            first = c.split("\n")[0]
            print(f"▸ {first}" + (" …" if "\n" in c else ""))
        if res:
            print(tidy_error(res, line_map) if re.search(r"\berror:", res) else res)
        if label and k < len(cmds) - 1:
            print()
    return 0


# ---------- entry points ----------

def locate_current(blocks, received):
    """Index of the block the plugin ran: exact match first, else the most similar (note may be unsaved)."""
    rc = received.strip()
    for i, b in enumerate(blocks):
        if b.strip() == rc:
            return i
    scores = [difflib.SequenceMatcher(None, b.strip(), rc).ratio() for b in blocks]
    return max(range(len(blocks)), key=scores.__getitem__) if scores and max(scores) > 0.3 else None


def main():
    argv = sys.argv[1:]
    if "--note" in argv:
        ap = argparse.ArgumentParser()
        ap.add_argument("--note", required=True)
        ap.add_argument("--block", type=int, required=True)
        ap.add_argument("--extra")
        a = ap.parse_args(argv)
        note = Path(a.note).resolve()
        blocks = haskell_blocks(note.read_text())
        code = blocks[a.block]
        if a.extra:
            code += "\n" + Path(a.extra).read_text()
        vault = next((p for p in note.parents if (p / ".obsidian").exists()), note.parent)
        sys.exit(run(blocks, a.block, note.parent, vault, current_code=code))

    # plugin mode: [-f ghc] file.hs
    tmpfile = Path(argv[-1])
    text = tmpfile.read_text()
    lines = text.split("\n")
    hdr = next((HEADER.match(l) for l in lines[:3] if HEADER.match(l)), None)
    body = "\n".join(l for l in lines if not HEADER.match(l))
    if not hdr:
        print("⚠️ No note path from the plugin (haskellInject should be `-- HSNOTE @vault_path @note_path`).\n"
              "Running this block on its own.")
        sys.exit(run([body], 0, tmpfile.parent, tmpfile.parent))
    vault, note_rel = Path(hdr.group(1)), hdr.group(2)
    note = vault / note_rel
    blocks = haskell_blocks(note.read_text()) if note.exists() else []
    cur = locate_current(blocks, body)
    if cur is None:
        blocks, cur = blocks + [body], len(blocks)
    sys.exit(run(blocks, cur, note.parent, vault, current_code=body))


if __name__ == "__main__":
    main()
