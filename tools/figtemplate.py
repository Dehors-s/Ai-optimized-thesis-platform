"""图表版式模板：列清单、看细节、画骨架、按内容选模板。

用法：
  py tools/figtemplate.py list
  py tools/figtemplate.py show T07_focus_context
  py tools/figtemplate.py render T07_focus_context --out figures/templates/T07.png
  py tools/figtemplate.py match --spatial --panels 5
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "paperkit" / "figures" / "templates.json"


def load() -> list[dict]:
    return json.loads(REG.read_text(encoding="utf-8"))["templates"]


def get(tid: str) -> dict:
    for t in load():
        if t["id"] == tid or t["id"].startswith(tid):
            return t
    raise SystemExit(f"没有模板 {tid}")


def rects(t: dict) -> dict[str, list[float]]:
    lay = t["layout"]
    if lay["type"] == "grid":
        rows, cols, gap = lay["rows"], lay["cols"], lay.get("gap", 0.03)
        out = {}
        for r in range(rows):
            for c in range(cols):
                w = (1 - gap * (cols - 1)) / cols
                h = (1 - gap * (rows - 1)) / rows
                out[f"r{r+1}c{c+1}"] = [c * (w + gap), 1 - (r + 1) * h - r * gap, w, h]
        return out
    if lay["type"] == "qualitative":
        rows, cols = lay["rows"], lay["cols"]
        out = {}
        w, h = 1 / cols, 1 / rows
        for r in range(rows):
            for c in range(cols):
                out[f"r{r+1}c{c+1}"] = [c * w, 1 - (r + 1) * h, w, h]
        return out
    return {k: v for k, v in lay.get("rects", {}).items()}


def render(t: dict, out: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    rs = rects(t)
    for i, (name, (x, y, w, h)) in enumerate(rs.items()):
        ax.add_patch(Rectangle((x, y), w, h, facecolor="#F2F5F8", edgecolor="#7A8A99",
                               lw=0.9, ls=(0, (4, 2))))
        ax.text(x + w / 2, y + h / 2, name, ha="center", va="center",
                fontsize=8, color="#44515C")
        if t.get("letters") and len(rs) <= 20:
            ax.text(x + 0.008, y + h - 0.012, f"({chr(97+i)})", ha="left", va="top",
                    fontsize=7, color="#333333")
    ax.text(0.0, 1.035, f"{t['id']}  {t['name']}", fontsize=11, fontweight="bold", va="bottom")
    ax.text(0.0, -0.045, "占位骨架：每个面板由 figspec 生成 PDF，再交给 Tavotto/Illustrator 拼版",
            fontsize=7.5, color="#666666", va="top")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=220, bbox_inches="tight")
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    return out


def match(args: argparse.Namespace) -> list[tuple[int, dict, str]]:
    n = args.panels
    scored = []
    for t in load():
        tid = t["id"]
        s, why = 0, ""
        if args.structure:
            if tid.startswith("T10"):
                s, why = 10, "有结构/流程内容"
            elif tid.startswith("T07"):
                s, why = 6, "需要总览+细节"
        elif args.qualitative:
            if tid.startswith("T09"):
                s, why = 10, "定性结果用矩阵"
            elif tid.startswith("T05"):
                s, why = 5, "多条件矩阵"
        elif args.spatial:
            if tid.startswith("T07") and n >= 4:
                s, why = 9, "空间总览 + 细节"
            elif tid.startswith("T04") and n == 4:
                s, why = 8, "2×2 空间对比"
            elif tid.startswith("T03") and n == 3:
                s, why = 8, "三联空间对比"
            elif tid.startswith("T01") and n <= 1:
                s, why = 7, "单张地图"
        elif args.temporal and n >= 4:
            if tid.startswith("T11"):
                s, why = 9, "多序列时序"
            elif tid.startswith("T06"):
                s, why = 5, "小倍数时间推进"
        elif args.distribution:
            if tid.startswith("T12"):
                s, why = 9, "分布+空间+关系混合"
            elif tid.startswith("T01"):
                s, why = 4, "单张分布图"
        if s == 0:
            if n <= 1 and tid.startswith("T01"):
                s, why = 3, "单面板"
            elif n == 2 and tid.startswith("T02"):
                s, why = 3, "双面板对照"
            elif n == 3 and tid.startswith("T03"):
                s, why = 3, "三联"
            elif n == 4 and tid.startswith("T04"):
                s, why = 3, "四宫格"
            elif 6 <= n <= 16 and tid.startswith("T05"):
                s, why = 3, "矩阵小倍数"
        if s:
            scored.append((s, t, why))
    scored.sort(key=lambda x: -x[0])
    return scored[:3]


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p = sub.add_parser("show")
    p.add_argument("id")
    p = sub.add_parser("render")
    p.add_argument("id")
    p.add_argument("--out", default="figures/templates/preview.png")
    p = sub.add_parser("match")
    p.add_argument("--spatial", action="store_true")
    p.add_argument("--temporal", action="store_true")
    p.add_argument("--qualitative", action="store_true")
    p.add_argument("--structure", action="store_true")
    p.add_argument("--distribution", action="store_true")
    p.add_argument("--panels", type=int, default=1)
    args = ap.parse_args()

    if args.cmd == "list":
        print("| id | 名称 | 面板 | 什么时候用 |")
        print("|---|---|---|---|")
        for t in load():
            lo, hi = t["panels"]
            print(f"| {t['id']} | {t['name']} | {lo}—{hi} | {t['when']} |")
    elif args.cmd == "show":
        t = get(args.id)
        print(json.dumps(t, ensure_ascii=False, indent=2))
    elif args.cmd == "render":
        print(render(get(args.id), Path(args.out)))
    else:
        for s, t, why in match(args):
            print(f"{s:2d}  {t['id']:22s} {t['name']:8s}  {why}")


if __name__ == "__main__":
    main()
