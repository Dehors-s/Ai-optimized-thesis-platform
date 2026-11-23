"""把图表语料做成可筛选的参考画廊（作者选图用）。

用法：
  py tools/gallery.py

产物：
  corpus/figures/corpus/gallery.html
  corpus/figures/corpus/gallery_thumbs/*.jpg
"""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus" / "figures" / "corpus"
THUMBS = CORPUS / "gallery_thumbs"
OUT = CORPUS / "gallery.html"

TYPE_ZH = {
    "map": "地图", "timeseries": "时序", "distribution": "分布", "scatter": "散点",
    "heatmap": "热力图", "architecture": "架构/框架", "qualitative": "定性结果",
    "profile": "剖面", "comparison": "对比", "evaluation": "评估", "other": "其他",
}
JOURNAL_ZH = {
    "gmd": "GMD", "essd": "ESSD", "nhess": "NHESS", "ocean": "Ocean",
    "acp": "ACP", "arxiv": "arXiv", "natcomms": "Nat Commun",
}


def main() -> None:
    man = {}
    for line in (CORPUS / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            man.setdefault(r["file"], r)

    labels = {}
    for fn in ("labels.csv", "labels_arxiv.csv"):
        p = CORPUS / fn
        if p.exists():
            for r in csv.DictReader(p.open(encoding="utf-8-sig")):
                if r["label"].strip():
                    labels[r["file"]] = r["label"].strip()

    cache = {}
    cp = CORPUS / "captions_zh.json"
    if cp.exists():
        cache = json.loads(cp.read_text(encoding="utf-8"))

    THUMBS.mkdir(parents=True, exist_ok=True)
    cards = []
    i = 0
    for f, r in man.items():
        p = ROOT / f
        if not p.exists():
            continue
        i += 1
        t = THUMBS / f"{i:03d}.jpg"
        if not t.exists():
            im = Image.open(p).convert("RGB")
            im.thumbnail((360, 260))
            im.save(t, "JPEG", quality=76)
        typ = labels.get(f, "unlabeled")
        journal = JOURNAL_ZH.get(r.get("journal", ""), r.get("journal", ""))
        cap = (cache.get(f) or r.get("caption", ""))[:220]
        rel = f.split("corpus/figures/corpus/", 1)[-1]
        cards.append(f"""<a class="card" href="{html.escape(rel)}" target="_blank"
            data-type="{typ}" data-journal="{html.escape(r.get('journal',''))}"
            data-text="{html.escape((cap + ' ' + r.get('title','')).lower())}">
            <img src="gallery_thumbs/{t.name}" loading="lazy">
            <div class="badge">{TYPE_ZH.get(typ, '未标')} · {html.escape(journal)}</div>
            <div class="cap">{html.escape(cap)}</div></a>""")

    types = [("all", "全部")] + [(k, v) for k, v in TYPE_ZH.items()] + [("unlabeled", "未标")]
    chips = "".join(f'<button data-type="{k}" class="chip{" active" if k=="all" else ""}">{v}</button>'
                    for k, v in types)
    doc = f"""<!doctype html><html lang="zh"><meta charset="utf-8">
<title>参考画廊（{len(cards)} 张）</title>
<style>
body{{font-family:"Microsoft YaHei",sans-serif;margin:20px;background:#f7f8fa;color:#222}}
h1{{font-size:20px}} .tip{{color:#666;font-size:13px;line-height:1.7}}
.bar{{position:sticky;top:0;background:#f7f8fa;padding:10px 0;z-index:2;display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
input{{padding:7px 10px;border:1px solid #cfd6dd;border-radius:6px;width:320px;font-size:13px}}
.chip{{border:1px solid #cfd6dd;background:#fff;border-radius:14px;padding:5px 10px;font-size:12px;cursor:pointer}}
.chip.active{{background:#1f6feb;color:#fff;border-color:#1f6feb}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px;margin-top:14px}}
.card{{background:#fff;border:1px solid #e3e6ea;border-radius:8px;text-decoration:none;color:#222;display:flex;flex-direction:column}}
.card img{{width:100%;height:170px;object-fit:contain;background:#fff;border-bottom:1px solid #f0f0f0}}
.badge{{font-size:11px;color:#777;padding:6px 8px 0}}
.cap{{font-size:11px;color:#444;padding:4px 8px 8px;line-height:1.5;height:64px;overflow:hidden}}
#count{{font-size:12px;color:#666}}
</style>
<h1>参考画廊：{len(cards)} 张</h1>
<p class="tip">按类型/来源筛选，或搜图注关键词。点开看原图；选中后可进入复刻流程。</p>
<div class="bar">
  <input id="q" placeholder="搜索图注关键词，如 map / segmentation / time series">
  <span id="count"></span>
</div>
<div class="bar">{chips}</div>
<div class="grid" id="grid">{''.join(cards)}</div>
<script>
let type="all";
const q=document.getElementById("q"), count=document.getElementById("count");
function apply(){{
  const s=q.value.toLowerCase(); let n=0;
  document.querySelectorAll(".card").forEach(c=>{{
    const okType = type==="all" || c.dataset.type===type;
    const okText = !s || c.dataset.text.includes(s);
    const show = okType && okText; c.style.display=show?"flex":"none"; if(show) n++;
  }});
  count.textContent=`显示 ${{n}} / ${{document.querySelectorAll(".card").length}}`;
}}
document.querySelectorAll(".chip").forEach(b=>b.onclick=()=>{{
  document.querySelectorAll(".chip").forEach(x=>x.classList.remove("active"));
  b.classList.add("active"); type=b.dataset.type; apply();
}});
q.oninput=apply; apply();
</script></html>"""
    OUT.write_text(doc, encoding="utf-8")
    print(f"written {OUT} ({len(cards)} cards)")


if __name__ == "__main__":
    main()
