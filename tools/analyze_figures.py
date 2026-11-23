"""统计图表语料库：面板数、长宽比、图注长度、结构类型。

用法：
  py tools/analyze_figures.py
  py tools/analyze_figures.py --json corpus/figures/corpus/stats.json

输入：corpus/figures/corpus/manifest.jsonl
输出：控制台表格 + stats.json
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus" / "figures" / "corpus"
MANIFEST = CORPUS / "manifest.jsonl"

TYPES = {
    "map": r"\bmap\b|\bmaps\b|spatial distribution|geographic|global distribution|grid cells|land cover"
           r"|study area|study region|location of|sampling sites|stations|spatial pattern",
    "timeseries": r"time series|temporal|seasonal|monthly|annual|interannual|trend|time evolution"
                  r"|daily|hourly|diurnal|cycle|evolution of",
    "distribution": r"violin|box ?plot|histogram|distribution of|density|frequency|spread|variability",
    "scatter": r"scatter|correlation|regression|relationship between|\br ?=",
    "heatmap": r"heat ?map|correlation matrix|confusion matrix",
    "architecture": r"framework|architecture|schematic|workflow|pipeline|diagram|illustration|conceptual"
                    r"|overview|structure of|components",
    "qualitative": r"qualitative|examples of|visuali[sz]ation|classification maps|segmentation|samples of"
                   r"|case study",
    "profile": r"cross[- ]section|vertical section|profile|transect",
    "comparison": r"comparison|compared|versus|\bvs\.?\b|against",
    "evaluation": r"evaluation|performance|skill|validation|accuracy|error",
}


def panel_count(caption: str) -> int:
    letters = set(re.findall(r"\(([a-hA-H])\)", caption))
    return len(letters) if letters else 1


def classify(caption: str) -> str:
    low = caption.lower()
    for name, pat in TYPES.items():
        if re.search(pat, low):
            return name
    return "other"


def bucket_aspect(r: float) -> str:
    if r < 1.0:
        return "<1 竖版"
    if r < 1.6:
        return "1.0-1.6"
    if r < 2.5:
        return "1.6-2.5"
    return ">2.5 横版"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(CORPUS / "stats.json"))
    ap.add_argument("--export-labels", type=int, default=0,
                    help="随机抽 N 张，导出 labels.csv 供人工填 label 列")
    ap.add_argument("--score-labels", default="",
                    help="读回填好的 labels.csv，算自动分类的准确率与混淆矩阵")
    args = ap.parse_args()

    rows, seen = [], set()
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r["file"] in seen:
            continue
        seen.add(r["file"])
        p = ROOT / r["file"]
        if not p.exists():
            continue
        try:
            w, h = Image.open(p).size
        except Exception:  # noqa: BLE001
            continue
        cap = r.get("caption", "")
        r.update({"w": w, "h": h, "aspect": round(w / h, 2),
                  "panels": panel_count(cap), "ctype": classify(cap),
                  "cap_len": len(re.findall(r"[\u4e00-\u9fff]|[A-Za-z]+", cap))})
        rows.append(r)

    if not rows:
        raise SystemExit("语料库为空，先跑 crawl_figures.py")

    by_j = Counter(r["journal"] for r in rows)
    panels = Counter(r["panels"] for r in rows)
    ctype = Counter(r["ctype"] for r in rows)
    aspect = Counter(bucket_aspect(r["aspect"]) for r in rows)
    cap_bins = Counter("<=40" if r["cap_len"] <= 40 else "41-80" if r["cap_len"] <= 80 else "81-150" if r["cap_len"] <= 150 else ">150" for r in rows)
    cross = defaultdict(Counter)
    for r in rows:
        cross[r["ctype"]][r["panels"]] += 1

    stats = {
        "n": len(rows), "by_journal": dict(by_j),
        "panels": dict(sorted(panels.items())),
        "types": ctype.most_common(),
        "aspect": dict(aspect), "cap_len": dict(cap_bins),
        "type_panels": {k: dict(v) for k, v in cross.items()},
        "median_panels": sorted(r["panels"] for r in rows)[len(rows) // 2],
        "median_aspect": sorted(r["aspect"] for r in rows)[len(rows) // 2],
        "median_cap": sorted(r["cap_len"] for r in rows)[len(rows) // 2],
    }
    Path(args.json).write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"图 {stats['n']} 张")
    print("期刊：", by_j)
    print("面板数：", dict(sorted(panels.items())), "中位数", stats["median_panels"])
    print("长宽比：", dict(aspect), "中位数", stats["median_aspect"])
    print("图注长度：", dict(cap_bins), "中位数", stats["median_cap"])
    print("类型：", ctype.most_common())
    print("\n类型 × 面板数：")
    for k, v in sorted(cross.items(), key=lambda x: -sum(x[1].values())):
        print(f"  {k:12s}", dict(sorted(v.items())))

    if args.export_labels:
        sample = random.sample(rows, min(args.export_labels, len(rows)))
        path = CORPUS / "labels.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["file", "journal", "auto_type", "panels", "caption", "label"])
            for r in sample:
                w.writerow([r["file"], r["journal"], r["ctype"], r["panels"],
                            r["caption"][:300], ""])
        print(f"\n已导出 {len(sample)} 张 → {path}")
        print("把每行的 label 填成 8 类之一；没填的行不参与评分。")
        print("类别：map / timeseries / distribution / scatter / heatmap / "
              "architecture / qualitative / profile / comparison / evaluation / other")

    if args.score_labels:
        path = Path(args.score_labels)
        rows_l = list(csv.DictReader(path.open(encoding="utf-8-sig")))
        pairs = [(r["auto_type"], r["label"].strip()) for r in rows_l if r.get("label", "").strip()]
        if not pairs:
            raise SystemExit("labels.csv 里没有已填的 label")
        ok = sum(1 for a, b in pairs if a == b)
        conf = defaultdict(Counter)
        for a, b in pairs:
            conf[a][b] += 1
        print(f"\n已标 {len(pairs)} 张，自动分类准确率 {ok/len(pairs):.0%}")
        print("混淆（行=自动，列=人工）：")
        labels = sorted({b for _, b in pairs})
        print("auto\\human", *labels, sep="\t")
        for a in sorted(conf):
            print(a, *[conf[a][b] for b in labels], sep="\t")


if __name__ == "__main__":
    main()
