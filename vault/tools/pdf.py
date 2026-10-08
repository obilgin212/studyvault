"""Textbook PDF helpers. Page numbers are PRINTED textbook pages; --offset converts to PDF pages.

  pdf.py info   <pdf>                      page count + text/images per page
  pdf.py text   <pdf> [first] [last]       no pages given = the WHOLE document; out-of-range pages are skipped
  pdf.py render <pdf> all <out-prefix>     every page -> <prefix>-p1.png, -p2.png, ...
  pdf.py render <pdf> <page> <out.png> [--offset N] [--zoom 2] [--clip x0,y0,x1,y1]
        (--clip: fractions of the page, e.g. 0,0.45,1,0.8 = full width, 45%-80% down; for showing one figure or example)
  pdf.py search <pdf> <regex> [--offset N]
  pdf.py split  <pdf> <outdir> <name>:<first>-<last> ... [--offset N]   (writes <outdir>/<name>.md)
  pdf.py pagemap <pdf>    detect printed page numbers -> <pdf>.pagemap.json (used automatically afterwards)

Scanned books often skip or duplicate pages, so a fixed offset drifts. Run `pagemap` once per textbook.
"""
import json
import os
import argparse
import re
from pathlib import Path

import pymupdf


PAGEMAP = {}  # printed page -> pdf page (1-based)


def to_pdf(printed, offset):
    if PAGEMAP:
        if printed in PAGEMAP:
            return PAGEMAP[printed]
        nearest = min(PAGEMAP, key=lambda k: abs(k - printed))
        return PAGEMAP[nearest] + (printed - nearest)
    return printed + offset


def to_printed(pdf_page, offset):
    if PAGEMAP:
        inv = {v: k for k, v in PAGEMAP.items()}
        if pdf_page in inv:
            return inv[pdf_page]
        nearest = min(inv, key=lambda k: abs(k - pdf_page))
        return inv[nearest] + (pdf_page - nearest)
    return pdf_page - offset


def page_text(doc, printed, offset):
    pdf_page = to_pdf(printed, offset)
    if not 1 <= pdf_page <= doc.page_count:
        return ""                                   # out of range: skip instead of crashing
    if PAGEMAP:
        label = f"textbook p.{printed} (pdf p.{pdf_page} of {doc.page_count})"
    else:
        label = f"page {pdf_page} of {doc.page_count}"
    return f"\n\n===== {label} =====\n" + doc[pdf_page - 1].get_text()


def build_pagemap(doc):
    """Read the page-number line in each page's header/footer; keep labels consistent with their neighbours."""
    raw = {}
    for i in range(doc.page_count):
        lines = [l.strip() for l in doc[i].get_text().splitlines() if l.strip()]
        for l in lines[:3] + lines[-2:]:
            if re.fullmatch(r"\d{1,4}", l) and abs((i + 1) - int(l)) < 80:
                raw[i + 1] = int(l)
                break
    pages = sorted(raw)
    good = {}
    for j, p in enumerate(pages):
        off = p - raw[p]
        near = [q - raw[q] for q in pages[max(0, j - 3):j + 4] if q != p]
        if near.count(off) >= 2:
            good[raw[p]] = p
    return good


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["text", "render", "search", "split", "pagemap", "info"])
    ap.add_argument("pdf")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--zoom", type=float, default=2.0)
    ap.add_argument("--clip", help="x0,y0,x1,y1 as fractions of the page")
    a = ap.parse_args()
    doc = pymupdf.open(a.pdf)
    map_path = Path(a.pdf + ".pagemap.json")
    if a.cmd == "pagemap":
        m = build_pagemap(doc)
        map_path.write_text(json.dumps(m))
        print(f"{len(m)} labelled pages -> {map_path}")
        return
    if map_path.exists():
        PAGEMAP.update({int(k): v for k, v in json.loads(map_path.read_text()).items()})

    if a.cmd == "info":
        print(f"{doc.page_count} pages")
        for i, pg in enumerate(doc):
            print(f"  page {i + 1}: {len(pg.get_text().strip())} chars of text, {len(pg.get_images())} image(s)")
        return
    if a.cmd == "text":
        # no page numbers = the WHOLE document (handouts: never assume page 1 is everything)
        if not a.args:
            first, last = (min(PAGEMAP), max(PAGEMAP)) if PAGEMAP else (1, doc.page_count)
        else:
            first = int(a.args[0])
            last = int(a.args[1]) if len(a.args) > 1 else first
        out = "".join(page_text(doc, p, a.offset) for p in range(first, last + 1))
        shown = sorted({to_pdf(p, a.offset) for p in range(first, last + 1)} & set(range(1, doc.page_count + 1)))
        print(f"[{doc.page_count} page(s) in this PDF; showing {len(shown)}]" + out)
        if not PAGEMAP and len(shown) < doc.page_count:
            rest = [n for n in range(1, doc.page_count + 1) if n not in shown]
            print(f"\n[NOT SHOWN: page(s) {rest[0]}–{rest[-1]} of {doc.page_count}. Read them too before helping.]")
    elif a.cmd == "render" and a.args[0] == "all":
        # render every page: out is a path prefix -> <prefix>-p1.png, <prefix>-p2.png, ...
        prefix = a.args[1].removesuffix(".png")
        for i, pg in enumerate(doc):
            f = f"{prefix}-p{i + 1}.png"
            pg.get_pixmap(matrix=pymupdf.Matrix(a.zoom, a.zoom)).save(f)
            print(f)
    elif a.cmd == "render":
        page, out = int(a.args[0]), a.args[1]
        pdf_page = to_pdf(page, a.offset)
        if not 1 <= pdf_page <= doc.page_count:
            raise SystemExit(f"page {page} doesn't exist: this PDF has {doc.page_count} page(s)")
        pg = doc[pdf_page - 1]
        clip = None
        if a.clip:
            x0, y0, x1, y1 = map(float, a.clip.split(","))
            # --clip is page fractions; pixel/point coords give an empty pixmap and a 0-byte PNG
            if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
                raise SystemExit(f"--clip {a.clip}: use fractions of the page (0-1) with x0<x1, y0<y1, e.g. 0.05,0.09,0.31,0.29")
            r = pg.rect
            clip = pymupdf.Rect(r.x0 + x0 * r.width, r.y0 + y0 * r.height, r.x0 + x1 * r.width, r.y0 + y1 * r.height)
        pix = pg.get_pixmap(matrix=pymupdf.Matrix(a.zoom, a.zoom), clip=clip)
        try:
            pix.save(out)
        except Exception:
            # don't leave a broken file behind: Obsidian caches it and keeps showing a broken image
            if os.path.exists(out):
                os.remove(out)
            raise
        print(out)
    elif a.cmd == "search":
        rx = re.compile(a.args[0], re.I)
        for i in range(doc.page_count):
            for line in doc[i].get_text().splitlines():
                if rx.search(line):
                    print(f"p.{to_printed(i + 1, a.offset)} (pdf {i + 1}): {line.strip()[:100]}")
    elif a.cmd == "split":
        outdir = Path(a.args[0])
        outdir.mkdir(parents=True, exist_ok=True)
        for spec in a.args[1:]:
            name, rng = spec.rsplit(":", 1)
            first, last = map(int, rng.split("-"))
            body = "".join(page_text(doc, p, a.offset) for p in range(first, last + 1))
            (outdir / f"{name}.md").write_text(f"# {name}\n{body}")
            print(outdir / f"{name}.md")


if __name__ == "__main__":
    main()
