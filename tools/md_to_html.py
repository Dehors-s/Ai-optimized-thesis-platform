"""Markdown → 单文件 HTML（支持表格、代码块、图片转 figure/figcaption）。"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import markdown

CSS = """
:root { --ink:#1f2328; --muted:#57606a; --line:#d0d7de; --bg:#ffffff; }
* { box-sizing: border-box; }
body { margin:0; background:#f6f7f9; color:var(--ink);
  font-family:"Source Han Serif SC","Songti SC","SimSun",serif; line-height:1.95; }
main { max-width: 880px; margin: 32px auto 80px; background:var(--bg);
  padding: 56px 64px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
h1 { font-family:"Source Han Sans SC","Microsoft YaHei",sans-serif; font-size:24px;
  line-height:1.5; text-align:center; margin:0 0 8px; }
h2 { font-family:"Source Han Sans SC","Microsoft YaHei",sans-serif; font-size:19px;
  margin:36px 0 12px; padding-bottom:6px; border-bottom:1px solid var(--line); }
h3 { font-family:"Source Han Sans SC","Microsoft YaHei",sans-serif; font-size:16px; margin:24px 0 8px; }
p { margin: 0 0 12px; text-align: justify; }
figure { margin: 22px 0; text-align:center; }
figure img { max-width:100%; height:auto; }
figcaption { font-size:13px; color:var(--muted); margin-top:6px; line-height:1.6; }
table { border-collapse: collapse; width:100%; margin:6px 0 18px; font-size:13px;
  border-top:1.4px solid #222; border-bottom:1.4px solid #222; }
th, td { border:none; border-bottom:1px solid #e3e6ea; padding:6px 8px;
  text-align:left; vertical-align:top; }
th { background:#fff; border-bottom:1px solid #222;
  font-family:"Source Han Sans SC","Microsoft YaHei",sans-serif; font-weight:600; }
tr:last-child td { border-bottom:none; }
code { background:#f3f4f6; padding:1px 4px; border-radius:3px; font-size:13px; }
pre { background:#f6f8fa; padding:12px; overflow:auto; border:1px solid var(--line); }
blockquote { border-left:3px solid var(--line); margin:12px 0; padding:4px 12px; color:var(--muted); }
@media (max-width: 720px) { main { padding: 24px 18px; margin: 0; } }
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", required=True)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    src = Path(args.md)
    text = src.read_text(encoding="utf-8")

    def repl(m):
        alt, path = m.group(1), m.group(2)
        return (f'<figure><img src="{path}" alt="">'
                f'<figcaption>{alt}</figcaption></figure>')

    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", repl, text)
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), src.stem)
    html = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{CSS}</style></head>
<body><main>{body}</main></body></html>"""
    out = Path(args.out) if args.out else src.with_suffix(".html")
    out.write_text(html, encoding="utf-8")
    print(out, len(html))


if __name__ == "__main__":
    main()
