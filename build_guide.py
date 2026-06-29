#!/usr/bin/env python3
"""Render a markdown doc into a static page, redacting private IPs before publishing.
Usage: python3 build_guide.py <source.md> <output.html> "<Page Title>"
"""
import re
import sys
from pathlib import Path

TEMPLATE = """<!doctype html>
<meta charset="utf-8">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
:root{{--bg:#f6f7fb;--card:#fff;--ink:#1d2433;--muted:#6b7280;--line:#e6e8ef;--accent:#3b5bdb}}
*{{box-sizing:border-box}}
body{{font-family:"Pretendard",system-ui,-apple-system,sans-serif;margin:0;background:var(--bg);color:var(--ink)}}
.wrap{{max-width:48rem;margin:0 auto;padding:2.5rem 2rem 4rem}}
nav a{{color:var(--accent);text-decoration:none;font-size:.85rem}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:.8rem;padding:2rem 2.2rem;box-shadow:0 1px 3px rgba(20,20,40,.04);margin-top:1rem}}
.card h1{{font-size:1.4rem}} .card h2{{font-size:1.15rem;border-top:1px solid var(--line);padding-top:1.2rem}}
.card table{{border-collapse:collapse;width:100%;font-size:.85rem}}
.card th,.card td{{border:1px solid var(--line);padding:.4rem .6rem;text-align:left}}
.card code{{background:var(--bg);padding:.1rem .35rem;border-radius:.3rem;font-size:.85em}}
.card pre{{background:var(--bg);padding:.8rem 1rem;border-radius:.5rem;overflow-x:auto}}
.card blockquote{{border-left:3px solid var(--accent);margin:0;padding:.3rem 1rem;color:var(--muted)}}
.card img{{max-width:100%;border-radius:.5rem}}
</style>
<div class="wrap">
<nav><a href="index.html">&larr; 데이터 카탈로그로 돌아가기</a></nav>
<div class="card" id="content"></div>
</div>
<script>
const SRC = {md_js_string};
document.getElementById("content").innerHTML = marked.parse(SRC);
</script>
"""


def main():
    src_path, out_path, title = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    text = src_path.read_text(encoding="utf-8")
    redacted = re.sub(r"\b10\.13\.10\.\d+\b", "10.x.x.x", text)  # ponytail: only this known private subnet is masked, extend if new sensitive ranges show up
    import json

    out_path.write_text(TEMPLATE.format(title=title, md_js_string=json.dumps(redacted)), encoding="utf-8")
    print(f"wrote {out_path} ({len(redacted)} chars rendered)")


def demo():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "t.md"
        src.write_text("# hi\nserver at 10.13.10.107 works")
        out = Path(d) / "t.html"
        sys.argv = ["x", str(src), str(out), "Test"]
        main()
        html = out.read_text()
        assert "10.13.10.107" not in html
        assert "10.x.x.x" in html
    print("OK: IP redaction verified")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        demo()
    else:
        main()
