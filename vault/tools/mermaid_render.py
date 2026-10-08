"""Render a Mermaid diagram to PNG so it can be checked by eye (used by the mermaid-maker agent).

  ~/miniconda3/envs/study/bin/python tools/mermaid_render.py <in.mmd> <out.png> [--theme default|dark]

Uses the local mermaid.js in tools/vendor (no network) and system Chrome in headless mode with a throwaway
profile, so it never touches the class-sync Chrome profile. Exits 1 and prints Mermaid's error on bad syntax.
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

TOOLS = Path(__file__).resolve().parent
MERMAID_JS = sorted((TOOLS / "vendor").glob("mermaid-*.min.js"))[-1]
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<style>body{margin:0;background:#fff;font-family:-apple-system,Helvetica,sans-serif}#out{display:inline-block;padding:16px}</style>
</head><body><div id="out"></div></body></html>"""

RENDER = """async ([src, theme]) => {
  mermaid.initialize({startOnLoad: false, theme, securityLevel: 'strict'});
  try {
    await mermaid.parse(src);
    const {svg} = await mermaid.render('m', src);
    document.getElementById('out').innerHTML = svg;
    const s = document.querySelector('#out svg');
    return {ok: true, nodes: document.querySelectorAll('#out .node').length,
            w: s.getBoundingClientRect().width, h: s.getBoundingClientRect().height};
  } catch (e) { return {ok: false, error: String(e.message || e)}; }
}"""


def render(src_path, out_path, theme="default"):
    src = Path(src_path).read_text()
    src = src.strip().removeprefix("```mermaid").removesuffix("```").strip()
    with sync_playwright() as p:
        kw = {"executable_path": CHROME} if Path(CHROME).exists() else {}
        b = p.chromium.launch(headless=True, **kw)
        page = b.new_page(viewport={"width": 1400, "height": 1000}, device_scale_factor=2)
        page.set_content(PAGE)
        page.add_script_tag(path=str(MERMAID_JS))
        res = page.evaluate(RENDER, [src, theme])
        if res.get("ok"):
            page.locator("#out").screenshot(path=str(out_path))
        b.close()
    return res


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    theme = sys.argv[sys.argv.index("--theme") + 1] if "--theme" in sys.argv else "default"
    if theme in args:
        args.remove(theme)
    if len(args) != 2:
        sys.exit(__doc__)
    r = render(args[0], args[1], theme)
    print(json.dumps(r))
    sys.exit(0 if r.get("ok") else 1)
