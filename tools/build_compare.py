"""生成原文/改写并排对照（HTML + Markdown）。"""

from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "outputs" / "论文版本" / "v1_原始.md"
NEW = ROOT / "outputs" / "论文版本" / "v1_分节改写.md"
OUT = ROOT / "outputs" / "论文版本"

NOTES = {
    "4.0": "分号串长句拆回句号；句均 52→56.6，逗号 1.95→2.30，的 3.12→3.22。",
    "4.1": "保留“含样本量混淆”的说明，叙述由分号改为句号。",
    "4.2": "漏斗数据合并为一句；保留“换干净划分为 0”的定性。",
    "4.3": "多时相与同日/跨日诊断合并叙述。",
    "7.0": "节首合并；删冗余“的”。",
    "7.1": "定义与三个数字合并为一句。",
    "7.2": "三类替代尝试合并为长句，保留全部数字。",
    "7.3": "有监督对照合并为一句，点明同一代理集、同一实现。",
    "7.4": "配额做法与空间平滑合并，前作声明保留。",
    "7.5": "收益分解保留公式与两个计数，句子合并。",
    "7.6": "平台证据合并，保留 0.0006 < 0.0061。",
    "7.7": "三条命题合并为一句长句；删 4 处引号与冗余“的”，的密度 3.98→3.22。",
}

SECTIONS = [
    ("4", "## 4 数据侧挖潜", "## 5 表示"),
    ("7", "## 7 开集处理：从检测到配额", "## 8 结果、归因与讨论"),
]


def section(text: str, start: str, end: str) -> str:
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j].strip()


def parse(block: str, prefix: str) -> dict[str, tuple[str, list[str]]]:
    """返回 {key: (标题, 段落列表)}，含 'x.0' 节首。"""
    parts = re.split(r"(?m)^###\s+([\d.]+)\s+(.+)$", block)
    # parts: [intro, num1, title1, body1, num2, title2, body2, ...]
    out: dict[str, tuple[str, list[str]]] = {}
    intro = parts[0]
    intro = re.sub(r"(?m)^##\s+.*$", "", intro, count=1).strip()
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", intro) if p.strip()]
    out[f"{prefix}.0"] = ("节首", paras)
    for k in range(1, len(parts), 3):
        num = parts[k].strip()
        title = parts[k + 1].strip()
        body = parts[k + 2]
        paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        out[num] = (f"{num} {title}", paras)
    return out


def main() -> None:
    old = OLD.read_text(encoding="utf-8")
    new = NEW.read_text(encoding="utf-8")

    pairs = []
    for prefix, a, b in SECTIONS:
        pairs.append((prefix, parse(section(old, a, b), prefix), parse(section(new, a, b), prefix)))

    # Markdown
    md = ["# 正文对照：v1 原始 vs v1 分节改写", "",
          "> 左/上为原文，右/下为改写。未列出的章节（1–3、5–6、8–9）两版相同。", ""]
    for prefix, o, n in pairs:
        md.append(f"## 第 {prefix} 章")
        keys = sorted(set(o) | set(n), key=lambda x: [int(t) if t.isdigit() else t for t in x.split(".")])
        for k in keys:
            if k.endswith(".0"):
                continue
            title = (n.get(k) or o.get(k))[0]
            md += [f"### {title}", "", f"> **改动**：{NOTES.get(k, '同义重写。')}", "", "**改前**", ""]
            md += [f"> {p}" for p in o.get(k, ("", []))[1]] or ["> （无）"]
            md += ["", "**改后**", ""]
            md += [f"> {p}" for p in n.get(k, ("", []))[1]] or ["> （无）"]
            md += [""]
    (OUT / "对照版.md").write_text("\n".join(md), encoding="utf-8")

    # HTML
    def esc(s: str) -> str:
        return html.escape(s)

    rows = []
    for prefix, o, n in pairs:
        keys = sorted(set(o) | set(n), key=lambda x: [int(t) if t.isdigit() else t for t in x.split(".")])
        for k in keys:
            if k.endswith(".0"):
                continue
            title = (n.get(k) or o.get(k))[0]
            left = "".join(f"<p>{esc(p)}</p>" for p in o.get(k, ("", []))[1]) or "<p class='empty'>（无）</p>"
            right = "".join(f"<p>{esc(p)}</p>" for p in n.get(k, ("", []))[1]) or "<p class='empty'>（无）</p>"
            rows.append(f"""
<section class="pair">
  <h3>{esc(title)}</h3>
  <p class="note">改动：{esc(NOTES.get(k, '同义重写。'))}</p>
  <div class="cols">
    <div class="col old"><div class="tag">改前</div>{left}</div>
    <div class="col new"><div class="tag">改后</div>{right}</div>
  </div>
</section>""")

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>正文对照：v1 原始 vs 分节改写</title>
<style>
body{{margin:0;background:#fff;color:#1f2328;font:15px/1.75 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif}}
.wrap{{max-width:1380px;margin:0 auto;padding:40px 28px 80px}}
h1{{font-size:26px;margin:0 0 6px}}
.sub{{color:#57606a;margin:0 0 26px}}
.metrics{{border-collapse:collapse;width:100%;font-size:14px;margin:0 0 34px}}
.metrics th,.metrics td{{border:1px solid #d0d7de;padding:7px 10px;text-align:left}}
.metrics th{{background:#f6f8fa}}
h2{{font-size:20px;margin:46px 0 16px;padding-top:16px;border-top:2px solid #d0d7de}}
.pair{{margin:22px 0 30px}}
h3{{font-size:16px;margin:0 0 4px}}
.note{{color:#57606a;font-size:13px;margin:0 0 10px}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.col{{border:1px solid #d0d7de;border-radius:8px;padding:12px 14px;background:#fff}}
.col.old{{background:#f6f8fa}}
.col p{{margin:0 0 10px}}
.tag{{font-size:12px;color:#57606a;letter-spacing:1px;margin-bottom:6px}}
.empty{{color:#8c959f}}
@media (max-width:900px){{.cols{{grid-template-columns:1fr}}}}
@media print{{body{{font-size:10.5pt}}.cols{{grid-template-columns:1fr 1fr}}}}
</style></head><body><div class="wrap">
<h1>正文对照：v1 原始 vs v1 分节改写</h1>
<p class="sub">左为原文，右为改写。未列出的章节（1–3、5–6、8–9）两版相同。</p>
<table class="metrics">
<tr><th>节</th><th>版本</th><th>句均长</th><th>逗号/句</th><th>的/百汉字</th><th>style_check</th></tr>
<tr><td>数据侧（4）</td><td>改前</td><td>52.0</td><td>1.95</td><td>3.12</td><td>84 / B</td></tr>
<tr><td>数据侧（4）</td><td>改后</td><td>56.6</td><td>2.30</td><td>3.22</td><td><b>100 / A</b></td></tr>
<tr><td>开集（7）</td><td>改前</td><td>53.2</td><td>1.73</td><td>3.98</td><td>54 / D</td></tr>
<tr><td>开集（7）</td><td>改后</td><td>60.2</td><td>2.03</td><td>3.22</td><td><b>92 / A</b></td></tr>
</table>
{''.join(rows)}
</div></body></html>"""
    (OUT / "对照版.html").write_text(doc, encoding="utf-8")
    print("written 对照版.md / 对照版.html", len(rows))


if __name__ == "__main__":
    main()
