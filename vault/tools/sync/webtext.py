"""Turn a public web page into readable Markdown (headings, paragraphs, lists, code blocks). Used to keep local
copies of class-site pages (e.g. a class website's problem sets) so the tutor can read them without going online."""
import re
import urllib.request
from html.parser import HTMLParser


class _MD(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out, self.pre, self.skip = [], False, 0

    def handle_starttag(self, t, a):
        if t in ("script", "style", "nav", "header", "footer"):
            self.skip += 1
        elif t == "pre":
            self.pre = True
            self.out.append("\n```\n")
        elif t in ("h1", "h2", "h3", "h4"):
            self.out.append("\n\n" + "#" * int(t[1]) + " ")
        elif t in ("p", "div", "section"):
            self.out.append("\n\n")
        elif t == "li":
            self.out.append("\n- ")
        elif t == "br":
            self.out.append("\n")
        elif t == "code" and not self.pre:
            self.out.append("`")

    def handle_endtag(self, t):
        if t in ("script", "style", "nav", "header", "footer"):
            self.skip = max(0, self.skip - 1)
        elif t == "pre":
            self.pre = False
            self.out.append("\n```\n")
        elif t == "code" and not self.pre:
            self.out.append("`")

    def handle_data(self, d):
        if not self.skip:
            self.out.append(d if self.pre else re.sub(r"\s+", " ", d))


def fetch_markdown(url, max_bytes=2_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (StudyVault personal notes)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        if "html" not in r.headers.get("content-type", ""):
            return None, None
        raw = r.read(max_bytes).decode("utf-8", "replace")
    title = re.search(r"<title>(.*?)</title>", raw, re.S | re.I)
    body = re.search(r"<main.*?>(.*)</main>", raw, re.S | re.I) or re.search(r"<body.*?>(.*)</body>", raw, re.S | re.I)
    p = _MD()
    p.feed(body.group(1) if body else raw)
    text = "".join(p.out)
    text = re.sub(r"^[ \t]*-[ \t]*$", "", text, flags=re.M)       # empty list items
    text = re.sub(r"^[ \t]+$", "", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return (title.group(1).strip() if title else url), text
