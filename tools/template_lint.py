"""面板模板 lint：按图类检查字号、图例、配色、白底、长宽比、边框。

用法：
  py tools/template_lint.py --all
  py tools/template_lint.py --template bar_group
  py tools/template_lint.py --all --json

图类阈值来自 docs/25 的语料观察；不同类别要求不同：
- 散点/分布：白底多、图例少、字号 ≥6；
- 定性：白底少、无图例、字号可小；
- 架构：长宽比宽、角色色 3—12、图例 ≤2；
- 热力：少色、字号可小、无图例。
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import to_rgba  # noqa: E402
from PIL import Image  # noqa: E402

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from paneltemplates import REG  # noqa: E402

CATEGORY = {
    "line_ci": "timeseries",
    "bar_group": "distribution",
    "scatter_fit": "scatter",
    "heatmap": "heatmap",
    "violin": "distribution",
    "contour": "field",
    "quiver": "field",
    "cnn": "architecture",
    "pipeline": "flow",
    "qualitative": "qualitative",
}

RULES = {
    "timeseries": {"font_min": 6.0, "legend_max": 3, "white": (0.50, 0.90),
                   "aspect": (1.2, 2.2), "spines_max": 0, "colors": None},
    "distribution": {"font_min": 6.0, "legend_max": 2, "white": (0.55, 0.90),
                     "aspect": (1.2, 2.0), "spines_max": 0, "colors": (2, 10)},
    "scatter": {"font_min": 6.0, "legend_max": 2, "white": (0.60, 0.95),
                "aspect": (1.0, 2.0), "spines_max": 0, "colors": (2, 8)},
    "heatmap": {"font_min": 4.5, "legend_max": 1, "white": (0.05, 0.70),
                "aspect": (0.8, 1.6), "spines_max": 0, "colors": None},
    "field": {"font_min": 5.0, "legend_max": 2, "white": (0.0, 0.95),
              "aspect": (1.0, 2.0), "spines_max": 0, "colors": None},
    "architecture": {"font_min": 5.5, "legend_max": 2, "white": (0.35, 0.80),
                     "aspect": (1.0, 2.6), "spines_max": 0, "colors": (3, 12)},
    "flow": {"font_min": 5.5, "legend_max": 0, "white": (0.50, 0.95),
             "aspect": (1.0, 3.2), "spines_max": 0, "colors": (2, 10)},
    "qualitative": {"font_min": 4.8, "legend_max": 0, "white": (0.0, 0.40),
                    "aspect": (1.1, 1.8), "spines_max": 0, "colors": None},
}


def _gray(rgb) -> bool:
    r, g, b = rgb[:3]
    return max(r, g, b) - min(r, g, b) < 0.06 or max(r, g, b) < 0.06


def render_metrics(name: str) -> dict:
    fig, ax = plt.subplots(figsize=(3.2, 2.6))
    if name in ("pipeline", "qualitative"):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
    REG[name](ax)

    texts = [t.get_fontsize() for t in ax.texts if str(t.get_text()).strip()]
    if not texts:
        texts = [t.get_fontsize() for t in ax.get_xticklabels() + ax.get_yticklabels()
                 if str(t.get_text()).strip()]
        texts += [ax.xaxis.label.get_fontsize(), ax.yaxis.label.get_fontsize()]
    leg = ax.get_legend()
    legend_entries = len(leg.get_texts()) if leg else 0
    colors = set()

    def add_color(c):
        try:
            rgba = to_rgba(c)
            if rgba[3] > 0.05 and not _gray(rgba):
                colors.add(tuple(round(float(x), 2) for x in rgba[:3]))
        except Exception:
            pass

    for p in ax.patches:
        add_color(p.get_facecolor())
    for c in ax.collections:
        try:
            for fc in c.get_facecolor():
                add_color(fc)
        except Exception:
            pass
    for line in ax.lines:
        add_color(line.get_color())
    spines = 0 if not ax.axison else sum(1 for s in ("top", "right")
                                         if ax.spines[s].get_visible())
    is3d = getattr(ax, "name", "") == "3d"

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "p.png"
        fig.savefig(p, dpi=200, bbox_inches="tight", pad_inches=0.02)
        plt.close(fig)
        im = Image.open(p).convert("RGB")
        a = np.asarray(im).astype(np.float32)
        white = float(((a[..., 0] > 245) & (a[..., 1] > 245) & (a[..., 2] > 245)).mean())
        aspect = im.width / im.height

    return {"font_min": min(texts) if texts else 0, "legend": legend_entries,
            "colors": len(colors), "spines": spines, "is3d": is3d,
            "white": white, "aspect": aspect}


def lint(name: str, metrics: dict | None = None) -> list[dict]:
    cat = CATEGORY.get(name, "distribution")
    m = metrics or render_metrics(name)
    rule = RULES.get(cat, RULES["distribution"])
    issues = []

    def add(level, rule_id, msg):
        issues.append({"level": level, "rule": rule_id, "msg": msg})

    if m["font_min"] < rule["font_min"]:
        add("fail", "R2", f"最小字号 {m['font_min']:.1f} < {rule['font_min']}")
    if m["legend"] > rule["legend_max"]:
        add("fail", "R5", f"图例 {m['legend']} 条 > {rule['legend_max']}")
    lo, hi = rule["white"]
    if not (lo <= m["white"] <= hi):
        add("warn", "R1", f"白底 {m['white']:.0%} 不在 {lo:.0%}—{hi:.0%}")
    lo, hi = rule["aspect"]
    if not (lo <= m["aspect"] <= hi):
        add("warn", "R7", f"长宽比 {m['aspect']:.2f} 不在 {lo}—{hi}")
    if m["spines"] > rule["spines_max"]:
        add("warn", "R1", f"上/右边框 {m['spines']} 条仍可见")
    if m["is3d"]:
        add("fail", "R1", "使用了 3D 坐标轴")
    if rule["colors"] is not None:
        cmin, cmax = rule["colors"]
        if not (cmin <= m["colors"] <= cmax):
            add("warn", "R3", f"角色色 {m['colors']} 种 不在 {cmin}—{cmax}")
    return issues


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--template", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    names = list(REG) if args.all else [args.template]
    out = []
    for name in names:
        m = render_metrics(name)
        issues = lint(name, m)
        score = 100 - 15 * sum(1 for i in issues if i["level"] == "fail") \
                    - 5 * sum(1 for i in issues if i["level"] == "warn")
        out.append({"template": name, "category": CATEGORY.get(name, "?"),
                    "score": max(0, score), "metrics": m, "issues": issues})
        if not args.json:
            flag = "PASS" if not issues else ("FAIL" if any(i["level"] == "fail" for i in issues) else "WARN")
            print(f"{name:14s} {CATEGORY.get(name,'?'):12s} {score:3d} {flag}")
            for i in issues:
                print(f"   [{i['level']}] {i['rule']} {i['msg']}")
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
