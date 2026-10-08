"""Run a Python file after turning leading tabs into 4 spaces.

Obsidian's Tab key can insert a real tab character, and Python refuses code that mixes tabs
and spaces in indentation (TabError / IndentationError). This only rewrites the whitespace at
the start of each line, so line numbers in error messages stay correct.
Called by tools/runpy as:  _tabfix_run.py <file.py> [args...]
"""
import re
import runpy
import sys
import traceback

path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    src = f.read()


def fix(line):
    ws = re.match(r"[ \t]*", line).group(0)
    return ws.replace("\t", "    ") + line[len(ws):] if "\t" in ws else line


fixed = "\n".join(fix(l) for l in src.split("\n"))
if fixed != src:
    with open(path, "w", encoding="utf-8") as f:   # the plugin's temp copy, not the note
        f.write(fixed)

sys.argv = sys.argv[1:]
try:
    runpy.run_path(path, run_name="__main__")
except SystemExit:
    raise
except BaseException as e:
    # Show only the frames from the user's code, not this launcher's.
    tb = e.__traceback__
    while tb is not None and tb.tb_frame.f_code.co_filename != path:
        tb = tb.tb_next
    traceback.print_exception(type(e), e, tb)
    sys.exit(1)
