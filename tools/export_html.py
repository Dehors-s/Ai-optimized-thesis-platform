"""把 README 与 docs/ 下的方案文档导出为单文件 HTML（便于直接阅读/分享）。

用法：py tools/export_html.py
产物：任务一成果.html
"""

from __future__ import annotations

import datetime
import pathlib
import re

import markdown

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "任务一成果.html"

PARTS = [
    ("part-overview", "总览", "README.md"),
    ("part-01", "一、方案总纲", "docs/01-方案总纲.md"),
    ("part-02", "二、文献与方法地图", "docs/02-文献与方法地图.md"),
    ("part-03", "三、质量评分卡", "docs/03-质量评分卡.md"),
    ("part-04", "四、端到端样例", "docs/04-端到端样例.md"),
    ("part-05", "五、中文期刊语体规则", "docs/05-中文期刊语体规则.md"),
    ("part-06", "六、方法 v2：语料标定", "docs/06-方法v2-语料标定.md"),
    ("part-07", "七、全文方法 v2.1", "docs/07-全文方法v2.1.md"),
    ("part-08", "八、方法叙事与重排", "docs/08-方法叙事与重排.md"),
    ("part-09", "九、四方向重排", "docs/09-四方向重排.md"),
    ("part-10", "十、术语治理", "docs/10-术语治理.md"),
    ("part-11", "十一、论文工具的复用架构", "docs/11-论文工具的复用架构.md"),
    ("part-12", "十二、竞品与取长补短", "docs/12-竞品与取长补短.md"),
    ("part-13", "十三、通用性审查", "docs/13-通用性审查.md"),
    ("part-14", "十四、通用管线与模板分离", "docs/14-通用管线与模板分离.md"),
    ("part-15", "十五、两种入口模式", "docs/15-两种入口模式.md"),
    ("part-prompts", "十六、提示词使用说明", "prompts/README.md"),
]

CSS = """
:root{--fg:#1f2328;--muted:#57606a;--line:#d0d7de;--bg:#fff;--soft:#f6f8fa;--accent:#0b5cad}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font:16px/1.75 -apple-system,"Segoe UI","Microsoft YaHei","Source Han Sans SC",sans-serif;}
.wrap{max-width:980px;margin:0 auto;padding:56px 32px 96px}
.cover{border-bottom:1px solid var(--line);padding-bottom:32px;margin-bottom:32px}
.cover h1{font-size:34px;line-height:1.3;margin:0 0 12px;letter-spacing:.5px}
.cover .sub{color:var(--muted);font-size:16px;margin:0 0 18px}
.cover .meta{color:var(--muted);font-size:13px;margin:0}
.cover .abstract{background:var(--soft);border-left:4px solid var(--accent);
  padding:16px 20px;margin:24px 0 0;font-size:15px;color:#30363d}
nav.toc{background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:16px 22px;margin:28px 0 40px}
nav.toc h2{font-size:15px;margin:0 0 10px;color:var(--muted);letter-spacing:1px}
nav.toc ol{margin:0;padding-left:22px;columns:2;column-gap:40px}
nav.toc a{color:var(--accent);text-decoration:none}
nav.toc a:hover{text-decoration:underline}
h1{font-size:26px;margin:64px 0 18px;padding-top:18px;border-top:2px solid var(--line)}
section:first-of-type h1{border-top:none;padding-top:0;margin-top:32px}
h2{font-size:21px;margin:38px 0 14px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:17px;margin:28px 0 10px}
h4{font-size:15px;margin:22px 0 8px;color:#30363d}
p{margin:12px 0}
ul,ol{padding-left:26px}
li{margin:5px 0}
blockquote{margin:16px 0;padding:10px 18px;border-left:4px solid var(--line);
  background:var(--soft);color:#30363d}
code{font-family:"Cascadia Code",Consolas,"Courier New",monospace;font-size:.9em;
  background:#eff1f3;border-radius:4px;padding:.15em .4em}
pre{background:#0d1117;color:#e6edf3;border-radius:8px;padding:16px 18px;overflow:auto;
  font-size:13.5px;line-height:1.6}
pre code{background:none;color:inherit;padding:0;font-size:inherit}
.table-wrap{overflow-x:auto;margin:16px 0}
table{border-collapse:collapse;width:100%;font-size:14.5px}
th,td{border:1px solid var(--line);padding:8px 10px;vertical-align:top;text-align:left}
th{background:var(--soft);font-weight:600;white-space:nowrap}
tr:nth-child(even) td{background:#fcfcfd}
hr{border:none;border-top:1px solid var(--line);margin:40px 0}
a{color:var(--accent)}
.footer{margin-top:64px;padding-top:20px;border-top:1px solid var(--line);
  color:var(--muted);font-size:13px}
@media print{
  body{font-size:11.5pt}
  .wrap{max-width:none;padding:0}
  nav.toc{break-after:page}
  h1{break-before:page}
  pre{white-space:pre-wrap}
  a{color:inherit;text-decoration:none}
}
"""


def convert(path: pathlib.Path) -> str:
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"],
        extension_configs={"toc": {"permalink": False}},
    )
    html = md.convert(path.read_text(encoding="utf-8"))
    # 表格横向滚动容器
    html = re.sub(r"<table>", '<div class="table-wrap"><table>', html)
    html = re.sub(r"</table>", "</table></div>", html)
    return html


def main() -> None:
    sections = []
    toc_items = []
    for anchor, title, rel in PARTS:
        html = convert(ROOT / rel)
        sections.append(f'<section id="{anchor}">\n{html}\n</section>')
        toc_items.append(f'<li><a href="#{anchor}">{title}</a></li>')

    today = datetime.date.today().isoformat()
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 论文质量提升方案 · 任务一成果</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

<header class="cover">
  <h1>AI 论文质量提升方案</h1>
  <p class="sub">任务一成果 · 论证优先的三层两环框架（ArgFirst）</p>
  <p class="meta">生成日期：{today}　|　工作区：{ROOT}</p>
  <div class="abstract">
    <b>一句话：</b>先立起可证伪的主张，再让每一句话、每一张图去兑现它。<br>
    论文质量是「论证必要性 × 证据可核性 × 语体合规性 × 呈现有效性」的乘积；
    AI 的通病是把这个乘积做成了加法。本方案用三层（论证 / 文本 / 视觉）承载内容，
    用两环（证据环 / 评审环）守住底线，并把三样东西做成可校验的契约：
    论证契约、语体契约、图表契约。
  </div>
</header>

<nav class="toc">
  <h2>目录</h2>
  <ol>{''.join(toc_items)}</ol>
</nav>

{''.join(sections)}

<div class="footer">
  本文由 <code>README.md</code> 与 <code>docs/</code> 下四份文档自动合并生成；
  完整的提示词（<code>prompts/</code>）、PaperIR schema 与示例（<code>spec/</code>）见工作区目录。
</div>

</div>
</body>
</html>
"""
    OUT.write_text(doc, encoding="utf-8")
    print(f"written: {OUT} ({len(doc):,} chars)")


if __name__ == "__main__":
    main()
