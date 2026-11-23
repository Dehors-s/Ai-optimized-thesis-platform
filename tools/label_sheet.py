"""生成图表标注页：缩略图 + 图注 + 自动类型，选完导出 labels.csv。

用法：
  py tools/label_sheet.py
  py tools/label_sheet.py --limit 100

产物：
  corpus/figures/corpus/label_sheet.html
  corpus/figures/corpus/thumbs/*.jpg
"""

from __future__ import annotations

import argparse
import html
import json
import random
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from analyze_figures import classify, panel_count  # noqa: E402
CORPUS = ROOT / "corpus" / "figures" / "corpus"
MANIFEST = CORPUS / "manifest.jsonl"
THUMBS = CORPUS / "thumbs"

CATS = [
    ("map", "地图 / 空间分布 / 研究区"),
    ("timeseries", "时间序列 / 季节 / 趋势"),
    ("distribution", "分布图：小提琴 / 箱线 / 直方图 / 密度"),
    ("scatter", "散点 / 相关 / 回归"),
    ("heatmap", "热力图 / 混淆矩阵 / 相关矩阵"),
    ("architecture", "网络结构 / 方法框架 / 流程示意"),
    ("qualitative", "定性结果 / 分类图 / 分割图 / 样例网格"),
    ("profile", "剖面 / 断面 / transect"),
    ("comparison", "多方法对比（非空间/时间）"),
    ("evaluation", "性能评估 / 误差指标"),
    ("other", "其他 / 不确定"),
]
CAT_ZH = {k: d for k, d in CATS}
JOURNAL_ZH = {
    "gmd": "GMD（地球科学模型发展）",
    "essd": "ESSD（地球系统科学数据）",
    "nhess": "NHESS（自然灾害与地球系统科学）",
    "natcomms": "Nature Communications",
    "arxiv": "arXiv",
}
TYPE_ZH = {
    "map": "地图", "timeseries": "时序", "distribution": "分布",
    "scatter": "散点", "heatmap": "热力图", "architecture": "架构/框架",
    "qualitative": "定性结果", "profile": "剖面", "comparison": "对比",
    "evaluation": "评估", "other": "其他",
}
FIX = [("培训", "训练"), ("神经网路", "神经网络"), ("机率", "概率"),
       ("解析度", "分辨率"), ("侦测", "检测"), ("卷积", "卷积")]


def fix_terms(s: str) -> str:
    for a, b in FIX:
        s = s.replace(a, b)
    return s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--journal", default="")
    ap.add_argument("--exclude", nargs="*", default=["labels.csv"])
    ap.add_argument("--out", default="label_sheet.html")
    ap.add_argument("--csv-name", default="labels.csv")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--thumbs", default="thumbs")
    ap.add_argument("--hide-auto", action="store_true")
    args = ap.parse_args()

    labeled = set()
    for fn in args.exclude:
        p0 = CORPUS / fn
        if p0.exists():
            import csv as _csv
            for r0 in _csv.DictReader(p0.open(encoding="utf-8-sig")):
                if r0.get("label", "").strip() or r0.get("file"):
                    labeled.add(r0["file"])

    rows, seen = [], set()
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r["file"] in seen or r["file"] in labeled:
            continue
        if args.journal and r.get("journal") != args.journal:
            continue
        seen.add(r["file"])
        p = ROOT / r["file"]
        if p.exists():
            r["_path"] = p
            r["ctype"] = classify(r.get("caption", ""))
            r["panels"] = panel_count(r.get("caption", ""))
            rows.append(r)
    if args.limit and len(rows) > args.limit:
        rows = random.Random(args.seed).sample(rows, args.limit)
        rows.sort(key=lambda x: x["file"])

    THUMBS = CORPUS / args.thumbs
    THUMBS.mkdir(parents=True, exist_ok=True)
    cache_path = CORPUS / "captions_zh.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    cards = []
    for i, r in enumerate(rows, 1):
        thumb = THUMBS / f"{i:03d}.jpg"
        im = Image.open(r["_path"]).convert("RGB")
        im.thumbnail((420, 300))
        im.save(thumb, "JPEG", quality=78)
        zh = fix_terms((cache.get(r["file"], "") or "").strip())
        en = r.get("caption", "")
        cap = (f"<div class='zh'>图注：{html.escape(zh)}</div>" if zh
               else "<div class='zh en-only'>（暂无中文，见下方英文）</div>")
        if en:
            cap += f"<details><summary>English</summary><div class='en'>{html.escape(en)}</div></details>"
        journal = JOURNAL_ZH.get(r.get("journal", ""), r.get("journal", ""))
        typ = TYPE_ZH.get(r.get("ctype", ""), r.get("ctype", ""))
        auto_txt = "" if args.hide_auto else f" · 自动判：{html.escape(typ)}"
        cards.append(f"""
        <div class="card">
          <img src="{args.thumbs}/{thumb.name}" loading="lazy">
          <div class="meta">#{i} · {html.escape(journal)}{auto_txt} · 面板 {r.get('panels',1)}</div>
          <div class="cap">{cap}</div>
          <select class="label" data-file="{html.escape(r['file'])}"
                  data-journal="{html.escape(r.get('journal',''))}"
                  data-auto="{html.escape(r.get('ctype',''))}"
                  data-panels="{r.get('panels',1)}">
            <option value="">— 未标 —</option>
            {''.join(f'<option value="{k}">{d}（{k}）</option>' for k, d in CATS)}
          </select>
        </div>""")

    opts = "".join(f"<li><b>{k}</b> — {d}</li>" for k, d in CATS)
    doc = f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<title>图表标注（{len(rows)} 张）</title>
<style>
body{{font-family:"Microsoft YaHei",sans-serif;margin:24px;background:#f7f8fa;color:#222}}
h1{{font-size:20px}} .tip{{color:#555;line-height:1.7;max-width:900px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;margin-top:20px}}
.card{{background:#fff;border:1px solid #e3e6ea;border-radius:8px;padding:10px;display:flex;flex-direction:column;gap:8px}}
.card img{{width:100%;height:210px;object-fit:contain;background:#fff;border:1px solid #f0f0f0}}
.meta{{font-size:11px;color:#777}}
.cap{{font-size:12px;color:#333;line-height:1.55;max-height:190px;overflow:auto}}
.cap .zh{{font-weight:600;margin-bottom:4px}}
.cap .en{{color:#777;font-size:11px;margin-top:2px}}
.cap details{{margin-top:4px;color:#777;font-size:11px}}
select{{width:100%;padding:6px;font-size:12px;border:1px solid #cfd6dd;border-radius:6px}}
.bar{{position:sticky;top:0;background:#f7f8fa;padding:10px 0;z-index:2;display:flex;gap:12px;align-items:center}}
button{{padding:8px 14px;font-size:13px;border:0;border-radius:6px;background:#1f6feb;color:#fff;cursor:pointer}}
button.secondary{{background:#e8edf3;color:#333}}
#count{{font-size:13px;color:#555}}
</style></head><body>
<h1>图表结构标注：{len(rows)} 张（{args.journal or "全部"}）</h1>
<div class="tip">
  <p><b>怎么标</b>：看图和图注，给每张选一个类型。只标结构，不评价好坏。拿不准选 <b>other</b>。</p>
  <p><b>类别</b>：</p><ul>{opts}</ul>
  <p>选完点“下载 {args.csv_name}”，保存到 <code>corpus/figures/corpus/{args.csv_name}</code>。
  选择会自动存在浏览器里，刷新不丢。</p>
</div>
<div class="bar">
  <button onclick="downloadCSV()">下载 {args.csv_name}</button>
  <button class="secondary" onclick="clearAll()">清空</button>
  <span id="count"></span>
</div>
<div class="grid">{''.join(cards)}</div>
<script>
const KEY = "figure-labels-{args.csv_name}";
function all() {{ return [...document.querySelectorAll("select.label")]; }}
function save() {{
  const m = {{}};
  all().forEach(s => {{ if (s.value) m[s.dataset.file] = s.value; }});
  localStorage.setItem(KEY, JSON.stringify(m));
  const n = all().filter(s => s.value).length;
  document.getElementById("count").textContent = `已标 ${{n}} / ${{all().length}}`;
}}
function load() {{
  const m = JSON.parse(localStorage.getItem(KEY) || "{{}}");
  all().forEach(s => {{ if (m[s.dataset.file]) s.value = m[s.dataset.file]; }});
  save();
}}
function esc(x) {{ return '"' + String(x).replace(/"/g, '""') + '"'; }}
function downloadCSV() {{
  const rows = [["file","journal","auto_type","panels","label"]];
  all().forEach(s => rows.push([s.dataset.file, s.dataset.journal, s.dataset.auto, s.dataset.panels, s.value]));
  const csv = "\\ufeff" + rows.map(r => r.map(esc).join(",")).join("\\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], {{type:"text/csv"}}));
  a.download = "{args.csv_name}"; a.click();
}}
function clearAll() {{
  if (!confirm("清空所有选择？")) return;
  all().forEach(s => s.value = ""); localStorage.removeItem(KEY); save();
}}
all().forEach(s => s.addEventListener("change", save));
load();
</script></body></html>"""

    out = CORPUS / args.out
    out.write_text(doc, encoding="utf-8")
    print(f"written {out}")
    print(f"thumbs {len(rows)} -> {THUMBS}")
    print(f"打开 HTML，逐张选类型，点“下载 {args.csv_name}”，保存到 corpus/figures/corpus/{args.csv_name}")


if __name__ == "__main__":
    main()
