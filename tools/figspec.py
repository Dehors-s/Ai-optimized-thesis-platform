"""图表规格渲染：从"要证明什么"出发，而不是从"画什么"出发。

用法：
  py tools/figspec.py demo   --out figures/demo
  py tools/figspec.py render --spec figures/spec/F1.json --out figures
  py tools/figspec.py lint   --spec figures/spec/F1.json

规格字段：
  id, claim, type, title, ylabel, xlabel, unit, caption,
  categories, values, ci, series, reference, highlight,
  nodes, matrix, row_labels, col_labels
类型：dot / waterfall / line / bar / heatmap / pipeline / map

设计规则见 docs/18-图表语法与生成.md；复杂图与工具链见 docs/19-复杂图表的技术路线.md。
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT / "corpus" / "geo"

OKABE = ["#000000", "#E69F00", "#56B4E9", "#009E73",
         "#F0E442", "#0072B2", "#D55E00", "#CC79A7"]
ACCENT = "#D55E00"
GREY = "#8C8C8C"
BLUE = "#0072B2"


def style() -> None:
    plt.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "grid.color": "#DDDDDD",
        "grid.linewidth": 0.6,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "svg.fonttype": "none",
    })


def _panel(spec: dict, w: float, h: float):
    fig, ax = plt.subplots(figsize=(w, h))
    return fig, ax


def draw_dot(ax, s: dict) -> None:
    cats = s["categories"]
    vals = s["values"]
    ci = s.get("ci") or []
    ys = list(range(len(cats)))[::-1]
    lo_all = min([c[0] for c in ci] + vals) if ci else min(vals)
    hi_all = max([c[1] for c in ci] + vals) if ci else max(vals)
    span = max(hi_all - lo_all, 1e-6)
    pad = span * 0.03
    for i, (c, v) in enumerate(zip(cats, vals)):
        color = ACCENT if c == s.get("highlight") else GREY
        right = ci[i][1] if ci else v
        if ci:
            lo, hi = ci[i]
            ax.errorbar(v, ys[i], xerr=[[v - lo], [hi - v]], fmt="o",
                        color=color, ecolor=color, elinewidth=1.1, capsize=2.5, ms=5)
        else:
            ax.plot(v, ys[i], "o", color=color, ms=5)
        ax.text(right + pad, ys[i], f"{v:g}",
                va="center", ha="left", fontsize=8, color="#333333")
    ref = s.get("reference") or {}
    if ref.get("band"):
        lo, hi = ref["band"]
        ax.axvspan(lo, hi, color="#BBBBBB", alpha=0.22, lw=0)
        ax.text((lo + hi) / 2, 0.96, ref.get("label", ""),
                transform=ax.get_xaxis_transform(), ha="center", va="top",
                fontsize=7.5, color="#555555",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
    elif ref.get("value") is not None:
        ax.axvline(ref["value"], color="#555555", ls=(0, (3, 2)), lw=1)
        ax.text(ref["value"], 0.96, ref.get("label", ""),
                transform=ax.get_xaxis_transform(), ha="center", va="top",
                fontsize=7.5, color="#555555",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
    ax.set_yticks(ys)
    ax.set_yticklabels(cats)
    ax.set_xlabel(s.get("xlabel", ""))
    ax.set_xlim(lo_all - pad, hi_all + span * 0.18)
    ax.set_ylim(-0.6, len(cats) - 0.15)
    ax.grid(False)


def draw_waterfall(ax, s: dict) -> None:
    steps = s["categories"]
    deltas = s["values"]
    base = float(s.get("base", 0))
    xs = list(range(len(steps)))
    spans = []
    cur = base
    for d in deltas:
        spans.append((cur, cur + d))
        cur += d
    lo = min([base] + [min(a, b) for a, b in spans])
    hi = max([base] + [max(a, b) for a, b in spans])
    rng = max(hi - lo, 1e-9)
    off = rng * 0.05
    pad = rng * 0.22
    fmt = s.get("delta_fmt") or ("+.4f" if rng < 0.1 else "+g")
    muted = set(s.get("muted") or [])

    for i, (x, name, d, (a, b)) in enumerate(zip(xs, steps, deltas, spans)):
        if d == 0:
            ax.plot(x, a, "o", color="#333333", ms=4)
        elif name in muted:
            ax.bar(x, d, bottom=a, color="#D9D9D9", width=0.55,
                   hatch="////", edgecolor="#8C8C8C", linewidth=0)
            ax.text(x, max(a, b) + off, format(d, fmt),
                    ha="center", va="bottom", fontsize=8, color="#666666")
        else:
            ax.bar(x, d, bottom=a, color=ACCENT if d >= 0 else "#7F7F7F", width=0.55)
            ax.text(x, max(a, b) + off, format(d, fmt),
                    ha="center", va="bottom", fontsize=8, color="#333333")
        if i < len(xs) - 1:
            ax.plot([x + 0.275, x + 0.725], [b, b],
                    color="#999999", lw=0.8, ls=":")
    ax.text(len(xs) - 1 + 0.34, spans[-1][1], f"{spans[-1][1]:.4f}",
            va="center", ha="left", fontsize=8, fontweight="bold", color="#222222")
    ax.set_xticks(xs)
    ax.set_xticklabels(steps, rotation=0)
    ax.set_ylabel(s.get("ylabel", ""))
    ax.set_xlim(-0.6, len(xs) - 1 + 0.95)
    ax.set_ylim(lo - pad, hi + pad)
    ax.grid(axis="y", color="#E8E8E8", linewidth=0.6)
    ax.set_axisbelow(True)


def draw_line(ax, s: dict) -> None:
    xs = s["xs"]
    series = s["series"]
    for i, (name, ys) in enumerate(series.items()):
        color = ACCENT if i == 0 else OKABE[(i % 7) + 1]
        ax.plot(xs, ys, "-o", color=color, lw=1.4, ms=3.5, label=name)
    if s.get("band"):
        lo, hi = s["band"]
        ax.fill_between(xs, lo, hi, color=ACCENT, alpha=0.15, lw=0)
    ax.set_xlabel(s.get("xlabel", ""))
    ax.set_ylabel(s.get("ylabel", ""))
    if len(series) > 1:
        ax.legend(frameon=False, loc="best")
    ax.grid(axis="y", alpha=0.5)
    ax.set_axisbelow(True)


def draw_bar(ax, s: dict) -> None:
    cats = s["categories"]
    series = s["series"]
    n = len(series)
    xs = list(range(len(cats)))
    width = 0.7 / max(n, 1)
    for i, (name, vals) in enumerate(series.items()):
        offs = (i - (n - 1) / 2) * width
        ax.bar([x + offs for x in xs], vals, width=width,
               color=OKABE[i % 7 + 1] if n > 1 else GREY, label=name)
    ax.set_xticks(xs)
    ax.set_xticklabels(cats)
    ax.set_ylabel(s.get("ylabel", ""))
    if n > 1:
        ax.legend(frameon=False, ncol=min(n, 3), loc="lower center",
                  bbox_to_anchor=(0.5, 1.0), borderaxespad=0)
    top = max(max(v) for v in series.values())
    if s.get("ylim"):
        ax.set_ylim(*s["ylim"])
    else:
        ax.set_ylim(0, top * 1.12)
    ax.grid(axis="y", alpha=0.5)
    ax.set_axisbelow(True)


def draw_heatmap(ax, s: dict) -> None:
    m = s["matrix"]
    im = ax.imshow(m, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(s["col_labels"])))
    ax.set_xticklabels(s["col_labels"], rotation=45, ha="right")
    ax.set_yticks(range(len(s["row_labels"])))
    ax.set_yticklabels(s["row_labels"])
    for i, row in enumerate(m):
        for j, v in enumerate(row):
            ax.text(j, i, f"{v:g}", ha="center", va="center", fontsize=7,
                    color="white" if v > 0.6 * max(max(r) for r in m) else "#333333")
    ax.set_xlabel(s.get("xlabel", ""))
    ax.set_ylabel(s.get("ylabel", ""), labelpad=18)


def draw_pipeline(ax, s: dict) -> None:
    nodes = s["nodes"]
    n = len(nodes)
    ax.set_xlim(0, n * 2.2)
    ax.set_ylim(0, 1)
    ax.axis("off")
    for i, node in enumerate(nodes):
        x = i * 2.2 + 0.15
        color = ACCENT if node.get("highlight") else "#F2F2F2"
        edge = ACCENT if node.get("highlight") else "#B0B0B0"
        box = FancyBboxPatch((x, 0.3), 1.8, 0.4, boxstyle="round,pad=0.02,rounding_size=0.06",
                             linewidth=1.0, facecolor=color, edgecolor=edge)
        ax.add_patch(box)
        ax.text(x + 0.9, 0.5, node["label"], ha="center", va="center",
                fontsize=8.5, color="white" if node.get("highlight") else "#222222",
                wrap=True)
        if i < n - 1:
            ax.add_patch(FancyArrowPatch((x + 1.82, 0.5), (x + 2.18, 0.5),
                                         arrowstyle="-|>", mutation_scale=8,
                                         color="#777777", lw=1.0))


_WORLD = None


def load_world() -> list:
    """Natural Earth 110m 国界多边形（公有领域），缓存一次。"""
    global _WORLD
    if _WORLD is not None:
        return _WORLD
    import shapefile  # pyshp
    shp = GEO / "countries" / "ne_110m_admin_0_countries.shp"
    if not shp.exists():
        raise SystemExit(f"缺少底图：{shp}（下载 Natural Earth 110m）")
    rings = []
    for sh in shapefile.Reader(str(shp)).shapes():
        pts, parts = sh.points, list(sh.parts) + [len(sh.points)]
        for i in range(len(parts) - 1):
            ring = pts[parts[i]:parts[i + 1]]
            if len(ring) >= 3:
                rings.append(ring)
    _WORLD = rings
    return rings


def load_places() -> list[dict]:
    import shapefile
    shp = GEO / "places" / "ne_110m_populated_places.shp"
    r = shapefile.Reader(str(shp))
    names = [f[0] for f in r.fields[1:]]
    i_pop = names.index("POP_MAX")
    out = []
    for rec, sh in zip(r.records(), r.shapes()):
        lon, lat = sh.points[0]
        out.append({"lon": lon, "lat": lat, "value": rec[i_pop]})
    return out


def draw_map(ax, s: dict) -> None:
    for ring in load_world():
        ax.add_patch(Polygon(ring, closed=True, facecolor="#F4F4F4",
                             edgecolor="#C4C4C4", linewidth=0.4, zorder=1))
    for lon in range(-180, 181, 60):
        ax.plot([lon, lon], [-60, 85], color="#E2E2E2", lw=0.4, ls=":", zorder=0)
    for lat in range(-60, 81, 30):
        ax.plot([-180, 180], [lat, lat], color="#E2E2E2", lw=0.4, ls=":", zorder=0)

    pts = s.get("points")
    if pts == "places":
        pts = load_places()
    if not pts:
        raise SystemExit("map 需要 points（列表或 \"places\"）")
    lons = [p["lon"] for p in pts]
    lats = [p["lat"] for p in pts]
    vals = [p.get("value", 0) for p in pts]
    if s.get("log"):
        vals = [math.log10(max(1, v)) for v in vals]

    bins = s.get("bins")
    cmap = plt.get_cmap(s.get("cmap", "YlGnBu"))
    if bins:
        norm = BoundaryNorm(bins, cmap.N)
        sc = ax.scatter(lons, lats, c=vals, cmap=cmap, norm=norm,
                        s=s.get("marker_size", 7), edgecolors="none", zorder=3)
    else:
        sc = ax.scatter(lons, lats, c=vals, cmap=cmap, vmin=s.get("vmin"),
                        vmax=s.get("vmax"), s=s.get("marker_size", 7),
                        edgecolors="none", zorder=3)

    w, e, south, north = s.get("region", [-180, 180, -60, 85])
    ax.set_xlim(w, e)
    ax.set_ylim(south, north)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks(range(-180, 181, 60))
    ax.set_yticks(range(-60, 91, 30))
    ax.set_xticklabels([f"{abs(x)}°{'W' if x < 0 else ('E' if x > 0 else '')}" for x in range(-180, 181, 60)],
                       fontsize=7)
    ax.set_yticklabels([f"{abs(y)}°{'S' if y < 0 else ('N' if y > 0 else '')}" for y in range(-60, 91, 30)],
                       fontsize=7)
    ax.tick_params(length=2, pad=1.5)
    ax.grid(False)
    cb = ax.figure.colorbar(sc, ax=ax, orientation="horizontal", fraction=0.04,
                            pad=0.08, aspect=45, shrink=0.55)
    cb.set_label(s.get("cbar_label", ""), fontsize=8)
    cb.ax.tick_params(labelsize=7, length=2)
    cb.outline.set_linewidth(0.4)
    if s.get("panel"):
        ax.text(0.01, 0.98, s["panel"], transform=ax.transAxes, ha="left", va="top",
                fontsize=9, fontweight="bold",
                bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none", alpha=0.85))


DRAW = {"dot": draw_dot, "waterfall": draw_waterfall, "line": draw_line,
        "bar": draw_bar, "heatmap": draw_heatmap, "pipeline": draw_pipeline,
        "map": draw_map}


def render(spec: dict, out: Path) -> list[Path]:
    style()
    w, h = spec.get("size", [4.2, 2.6])
    fig, ax = _panel(spec, w, h)
    DRAW[spec["type"]](ax, spec)
    if spec.get("title") and spec.get("show_title"):
        ax.set_title(spec["title"], loc="left", fontweight="bold", pad=8)
    out.parent.mkdir(parents=True, exist_ok=True)
    png, svg, pdf = out.with_suffix(".png"), out.with_suffix(".svg"), out.with_suffix(".pdf")
    fig.savefig(png)
    fig.savefig(svg)
    fig.savefig(pdf)          # 矢量 PDF，交给 Tavotto / Illustrator 拼版
    plt.close(fig)
    return [png, svg, pdf]


def lint(spec: dict) -> list[str]:
    issues = []
    t = spec.get("type")
    if t not in DRAW:
        issues.append(f"未知类型 {t}")
        return issues
    if not spec.get("claim"):
        issues.append("缺少 claim（这张图支持哪条主张）")
    else:
        if spec["claim"] not in (spec.get("caption") or ""):
            issues.append("图注没有提到 claim 编号")
    if not (spec.get("caption") or "").strip():
        issues.append("缺少图注")
    if t in ("waterfall", "line", "bar", "heatmap") and not spec.get("ylabel"):
        issues.append("缺少纵轴标题")
    if t == "dot" and not spec.get("xlabel"):
        issues.append("缺少横轴标题")
    if t not in ("pipeline", "map") and "unit" not in spec:
        issues.append("缺少 unit 字段（无单位就写空串）")
    w, h = spec.get("size", [4.2, 2.6])
    if w > 7.2:
        issues.append(f"宽度 {w}in 超过双栏 7.2in")
    if h > 9:
        issues.append(f"高度 {h}in 过大")
    if t in ("dot", "waterfall", "bar", "line", "heatmap"):
        data = spec.get("values") or spec.get("series") or spec.get("matrix")
        if not data:
            issues.append("没有数据")
    colors = spec.get("colors")
    if colors and any(c.lower() not in [x.lower() for x in OKABE] for c in colors):
        issues.append("配色不在 Okabe-Ito 色盲安全表内")
    if t == "pipeline" and not spec.get("nodes"):
        issues.append("pipeline 没有节点")
    if t == "map":
        if not spec.get("points"):
            issues.append("map 缺少 points")
        if not spec.get("cbar_label"):
            issues.append("map 缺少 cbar_label")
    if t == "bar" and not spec.get("ylim"):
        vals = [v for vs in spec.get("series", {}).values() for v in vs]
        if vals and min(vals) > 0:
            span = (max(vals) - min(vals)) / max(vals)
            if span < 0.2:
                issues.append("柱状图从 0 起且组间差异小于 20%，差异会被压缩；"
                              "改用 dot/waterfall，或显式给 ylim")
    return issues


def demo(out: Path) -> None:
    specs = [
        {
            "id": "F1", "claim": "C-03", "type": "dot",
            "title": "后处理增益低于噪声下限",
            "xlabel": "宏平均 F1 变化（×10^-3）", "ylabel": "", "unit": "×10^-3",
            "categories": ["数据预处理", "异构骨干", "训练后处理", "对照"],
            "values": [6.0, 4.6, 1.4, 0.0],
            "ci": [[5.2, 6.8], [3.9, 5.3], [0.9, 1.9], [0.0, 0.0]],
            "reference": {"band": [1.8, 2.2], "label": "噪声下限"},
            "highlight": "训练后处理",
            "size": [4.4, 2.5],
            "caption": "图 1 训练后处理的增益为 0.0014，低于 0.002 的噪声下限（C-03）。"
                       "横轴为相对对照的宏平均 F1 变化，误差条为五个随机种子的 95% 区间；"
                       "灰带为重复测量得到的噪声下限。因此本文不主张后处理带来可分辨的提升。",
        },
        {
            "id": "F2", "claim": "C-04", "type": "waterfall",
            "title": "三项改动对最终结果的累计贡献",
            "ylabel": "宏平均 F1", "unit": "macro-F1",
            "base": 0.6520,
            "categories": ["基线", "预处理", "异构骨干", "后处理"],
            "values": [0.0, 0.0041, 0.0023, 0.0014],
            "muted": ["后处理"],
            "size": [4.6, 2.6],
            "caption": "图 2 三项改动累计把宏平均 F1 从 0.6520 推到 0.6598（C-04）。"
                       "柱高为相对上一步的增量，虚线连接累计值；斜纹柱表示增量落在噪声下限内，不计入结论。"
                       "最大单项来自预处理，后处理最小且不可分辨。",
        },
        {
            "id": "F3", "claim": "C-01", "type": "pipeline",
            "title": "",
            "nodes": [
                {"label": "数据检查\n日期/重叠/先验"},
                {"label": "预处理\n拼接/迁移/双表示"},
                {"label": "异构骨干\n四族十七成员"},
                {"label": "后处理\n重标定/精修/配额", "highlight": True},
            ],
            "size": [7.0, 1.5],
            "caption": "图 3 按问题来源分工的四段流程（C-01）。"
                       "橙色为本文改动最集中的一段；箭头表示数据流向，不是模块调用顺序。",
        },
        {
            "id": "F4", "claim": "C-05", "type": "map",
            "points": "places", "log": True,
            "cmap": "YlGnBu", "vmin": 2.5, "vmax": 7.5,
            "cbar_label": "log10(人口)", "marker_size": 6,
            "size": [7.2, 3.6],
            "caption": "图 4 全球城市人口分布（C-05，示例数据来自 Natural Earth）。"
                       "点为人口≥1000 的城镇居民点，颜色为人口的对数；"
                       "底图为 110m 国界，仅作定位用。",
        },
    ]
    out.mkdir(parents=True, exist_ok=True)
    for s in specs:
        issues = lint(s)
        files = render(s, out / s["id"])
        (out / f"{s['id']}.json").write_text(
            json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{s['id']}: {', '.join(str(f) for f in files)}"
              + (f" | lint: {issues}" if issues else " | lint ok"))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("render")
    p.add_argument("--spec", required=True)
    p.add_argument("--out", default="figures")
    p = sub.add_parser("lint")
    p.add_argument("--spec", required=True)
    p = sub.add_parser("demo")
    p.add_argument("--out", default="figures/demo")
    args = ap.parse_args()

    if args.cmd == "demo":
        demo(Path(args.out))
        return
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    if args.cmd == "lint":
        issues = lint(spec)
        print("\n".join(issues) if issues else "ok")
    else:
        out = Path(args.out) / spec["id"]
        print(render(spec, out))


if __name__ == "__main__":
    main()
