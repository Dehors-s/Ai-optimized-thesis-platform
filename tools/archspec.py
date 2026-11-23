"""架构图 DSL：用节点/连线/分组/放大框画神经网络与系统架构图。

用法：
  py tools/archspec.py demo --out figures/arch
  py tools/archspec.py render --spec figures/arch/A1.json --out figures/arch
  py tools/archspec.py lint   --spec figures/arch/A1.json

设计目标（来自 docs/21）：
- 主链 ≤7 节点；超出就折叠进放大框，不缩字号；
- 节点等宽等高、网格对齐；
- 连线正交，分叉从同一出口；
- 颜色编码角色（数据/模块/本文/冻结/损失）；
- 放大框用虚线锚回被放大的节点；
- 导出 PNG + SVG + PDF，交给 Tavotto/Illustrator 拼版。
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

KIND = {
    "data": ("#E3F0FA", "#5B9BD5"),
    "module": ("#F2F2F2", "#999999"),
    "ours": ("#FBE3D2", "#D55E00"),
    "frozen": ("#DDEEF9", "#4C9BD1"),
    "loss": ("#E2F0D9", "#548235"),
    "op": ("#FFFFFF", "#333333"),
}
ARROW = "#555555"


def _bbox(nodes: list[dict], cols: int, rows: int, area: tuple[float, float, float, float],
          node_w: float, node_h: float, vertical: bool = False) -> dict[str, tuple[float, float]]:
    x0, y0, w, h = area
    if vertical:
        sx, sy = w / max(rows, 1), h / max(cols, 1)      # 横向 lane / 纵向 step
        out = {n["id"]: (x0 + (n["row"] + 0.5) * sx,
                         y0 + h - (n["col"] + 0.5) * sy) for n in nodes}
    else:
        sx, sy = w / max(cols, 1), h / max(rows, 1)
        out = {n["id"]: (x0 + (n["col"] + 0.5) * sx,
                         y0 + h - (n["row"] + 0.5) * sy) for n in nodes}
    return out


def _box(ax, cx, cy, w, h, label, kind="module", fs=7.4):
    face, edge = KIND.get(kind, KIND["module"])
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                boxstyle="round,pad=0.004,rounding_size=0.012",
                                facecolor=face, edgecolor=edge, linewidth=0.9, zorder=2))
    ax.text(cx, cy, label, ha="center", va="center", fontsize=fs,
            color="#1F1F1F", zorder=3, linespacing=1.25)


def _edge(ax, p1, p2, style="-", label="", route="auto"):
    (x1, y1), (x2, y2) = p1, p2
    if route == "side":
        xr = max(x1, x2) + 0.035
        pts = [(x1, y1), (xr, y1), (xr, y2), (x2, y2)]
    elif abs(x1 - x2) < 1e-6:
        pts = [(x1, y1), (x1, y2)]
    elif abs(y1 - y2) < 1e-6:
        pts = [(x1, y1), (x2, y2)]
    elif abs(x2 - x1) > abs(y2 - y1):
        mx = (x1 + x2) / 2
        pts = [(x1, y1), (mx, y1), (mx, y2), (x2, y2)]
    else:
        my = (y1 + y2) / 2
        pts = [(x1, y1), (x1, my), (x2, my), (x2, y2)]
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=ARROW, lw=0.9, ls=style, zorder=1,
            solid_capstyle="round")
    ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>",
                                 mutation_scale=7, color=ARROW, lw=0.9, zorder=1.5))
    if label:
        if abs(y1 - y2) < 1e-6:
            ax.text((x1 + x2) / 2, y1 + 0.014, label, ha="center", va="bottom",
                    fontsize=6.1, color="#666666",
                    bbox=dict(boxstyle="round,pad=0.10", fc="white", ec="none", alpha=0.9),
                    zorder=4)
        else:
            ax.text((x1 + x2) / 2 + 0.008, (y1 + y2) / 2, label, ha="left", va="center",
                    fontsize=6.1, color="#666666",
                    bbox=dict(boxstyle="round,pad=0.10", fc="white", ec="none", alpha=0.9),
                    zorder=4)


def _group(ax, centers, members, label, kind="frozen"):
    pts = [centers[m] for m in members if m in centers]
    if not pts:
        return
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    pad = 0.075
    x0, y0 = min(xs) - pad, min(ys) - pad
    w, h = max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad
    _, edge = KIND.get(kind, KIND["frozen"])
    ax.add_patch(Rectangle((x0, y0), w, h, fill=False, edgecolor=edge,
                           lw=0.8, ls=(0, (4, 2)), zorder=0))
    ax.text(x0 + 0.004, y0 + h + 0.006, label, ha="left", va="bottom",
            fontsize=6.3, color=edge, zorder=4)


def render(spec: dict, out: Path) -> list[Path]:
    W, H = spec.get("width", 7.2), spec.get("height", 3.6)
    fig, ax = plt.subplots(figsize=(W, H))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    nodes = spec.get("nodes", [])
    cols = max((n["col"] for n in nodes), default=0) + 1
    rows = max((n["row"] for n in nodes), default=0) + 1
    default_area = [0.17, 0.08, 0.81, 0.86] if spec.get("row_labels") else [0.04, 0.10, 0.92, 0.84]
    area = tuple(spec.get("area", default_area))
    vertical = spec.get("direction") == "vertical"
    if vertical:
        node_w = min(0.30, (area[2] / rows) * 0.72)
        node_h = min(0.11, (area[3] / cols) * 0.55)
    else:
        node_w = min(0.16, (area[2] / cols) * 0.66)
        node_h = min(0.13, (area[3] / rows) * 0.60)
    centers = _bbox(nodes, cols, rows, area, node_w, node_h, vertical)

    x0, y0, aw, ah = area
    for ysep in spec.get("separators", []):
        ax.plot([x0, x0 + aw], [ysep, ysep], color="#BBBBBB", lw=0.7, ls=(0, (2, 3)), zorder=0)
    for rl in spec.get("row_labels", []):
        cy = y0 + ah - (rl["row"] + 0.5) * (ah / rows)
        ax.text(0.004, cy, rl["label"], ha="left", va="center", fontsize=7.6,
                fontweight="bold", color="#333333")

    for g in spec.get("groups", []):
        _group(ax, centers, g.get("nodes", []), g.get("label", ""), g.get("kind", "frozen"))

    for n in nodes:
        cx, cy = centers[n["id"]]
        fs = n.get("fontsize", 6.8 if vertical else 7.4)
        _box(ax, cx, cy, node_w * n.get("w", 1), node_h * n.get("h", 1),
             n.get("label", ""), n.get("kind", "module"), fs)

    for e in spec.get("edges", []):
        a, b = e["from"], e["to"]
        if a not in centers or b not in centers:
            continue
        (x1, y1), (x2, y2) = centers[a], centers[b]
        route = e.get("route", "auto")
        if route == "side":
            p1, p2 = (x1 + node_w / 2, y1), (x2 + node_w / 2, y2)
        elif abs(x2 - x1) >= abs(y2 - y1):
            p1, p2 = (x1 + node_w / 2, y1), (x2 - node_w / 2, y2)
        else:
            p1, p2 = (x1, y1 - node_h / 2), (x2, y2 + node_h / 2)
        _edge(ax, p1, p2, e.get("style", "-"), e.get("label", ""), route)

    for a in spec.get("annotations", []):
        ax.text(a["x"], a["y"], a["text"], ha=a.get("ha", "left"), va=a.get("va", "center"),
                fontsize=a.get("fontsize", 8), color=a.get("color", "#333333"),
                fontweight=a.get("weight", "normal"))

    z = spec.get("zoom")
    if z:
        zx, zy, zw, zh = z.get("rect", [0.52, 0.02, 0.44, 0.34])
        ax.add_patch(Rectangle((zx, zy), zw, zh, fill=False, edgecolor="#999999",
                               lw=0.8, ls=(0, (4, 2)), zorder=1))
        ax.text(zx + 0.008, zy + zh - 0.012, z.get("title", ""), ha="left", va="top",
                fontsize=7.0, color="#444444", zorder=4)
        zn = z.get("nodes", [])
        if zn:
            zcols = max(n["col"] for n in zn) + 1
            zrows = max(n["row"] for n in zn) + 1
            zcent = _bbox(zn, zcols, zrows, (zx + 0.012, zy + 0.012, zw - 0.024, zh - 0.05),
                          node_w * 0.55, node_h * 0.55)
            zcell_w = (zw - 0.024) / zcols
            zcell_h = (zh - 0.05) / zrows
            for n in zn:
                cx, cy = zcent[n["id"]]
                _box(ax, cx, cy, zcell_w * 0.80, zcell_h * 0.55,
                     n.get("label", ""), n.get("kind", "module"), 6.4)
            for e in z.get("edges", []):
                a, b = e["from"], e["to"]
                if a in zcent and b in zcent:
                    (x1, y1), (x2, y2) = zcent[a], zcent[b]
                    _edge(ax, (x1 + zcell_w * 0.40, y1), (x2 - zcell_w * 0.40, y2),
                          e.get("style", "-"), "")
        src = z.get("source")
        if src in centers:
            sx, sy = centers[src]
            ax.plot([sx, sx, zx + zw / 2], [sy - node_h / 2, zy + zh + 0.02, zy + zh + 0.02],
                    color="#999999", lw=0.7, ls=(0, (2, 2)), zorder=0)

    if spec.get("title"):
        ax.text(0.004, 1.01, spec["title"], ha="left", va="bottom",
                fontsize=9, fontweight="bold", color="#222222")

    out.parent.mkdir(parents=True, exist_ok=True)
    files = []
    for ext in ("png", "svg", "pdf"):
        p = out.with_suffix(f".{ext}")
        fig.savefig(p, dpi=300, bbox_inches="tight", pad_inches=0.02)
        files.append(p)
    plt.close(fig)
    return files


def lint(spec: dict) -> list[str]:
    issues = []
    nodes = spec.get("nodes", [])
    if not nodes:
        issues.append("没有节点")
        return issues
    cols = max(n["col"] for n in nodes) + 1
    if cols > 7:
        issues.append(f"主链 {cols} 个节点，超过 7；应折叠进放大框")
    for n in nodes:
        if len(n.get("label", "").replace("\n", "")) > 24:
            issues.append(f"节点 {n['id']} 标签过长（>24 字），考虑换行或缩写")
    ids = {n["id"] for n in nodes}
    for e in spec.get("edges", []):
        if e["from"] not in ids or e["to"] not in ids:
            issues.append(f"边 {e['from']}→{e['to']} 引用了不存在的节点")
    if spec.get("zoom") and spec["zoom"].get("source") not in ids:
        issues.append("zoom.source 不在节点里")
    if not spec.get("caption"):
        issues.append("缺少图注")
    return issues


def demo(out: Path) -> None:
    specs = [
        {
            "id": "A1", "claim": "C-01", "title": "",
            "width": 7.2, "height": 2.3,
            "nodes": [
                {"id": "img0", "col": 0, "row": 0, "label": "RGB/MSI\n固定通道", "kind": "data"},
                {"id": "bb", "col": 1, "row": 0, "label": "Backbone", "kind": "module"},
                {"id": "tune", "col": 2, "row": 0, "label": "逐任务微调\n(Tuned ×N)", "kind": "ours"},
                {"id": "task0", "col": 3, "row": 0, "label": "Task 1..N", "kind": "module"},
                {"id": "img1", "col": 0, "row": 1, "label": "HSI\n可变通道", "kind": "data"},
                {"id": "prompt", "col": 1, "row": 1, "label": "Task\nPrompts", "kind": "module"},
                {"id": "hf", "col": 2, "row": 1, "label": "HyperFree\n(frozen)", "kind": "frozen"},
                {"id": "mask", "col": 3, "row": 1, "label": "Multi-mask", "kind": "module"},
            ],
            "edges": [
                {"from": "img0", "to": "bb"},
                {"from": "bb", "to": "tune", "label": "fine-tune"},
                {"from": "tune", "to": "task0"},
                {"from": "img1", "to": "prompt"},
                {"from": "prompt", "to": "hf"},
                {"from": "hf", "to": "mask", "label": "freeze"},
            ],
            "separators": [0.50],
            "row_labels": [{"row": 0, "label": "(a) 主流范式"},
                           {"row": 1, "label": "(b) 本文"}],
            "caption": "图 1 两条范式的差别只在通道是否可变、骨干是否冻结（C-01）。"
                       "上行每换一个任务就要重训一份权重；下行共享冻结骨干，靠 prompt 适配任务。",
        },
        {
            "id": "A2", "claim": "C-02", "title": "",
            "width": 7.2, "height": 4.2,
            "area": [0.04, 0.54, 0.92, 0.38],
            "nodes": [
                {"id": "in", "col": 0, "row": 0, "label": "输入\nH×W×C", "kind": "data"},
                {"id": "enc", "col": 1, "row": 0, "label": "Encoder", "kind": "module"},
                {"id": "btn", "col": 2, "row": 0, "label": "Bottleneck", "kind": "ours"},
                {"id": "dec", "col": 3, "row": 0, "label": "Decoder", "kind": "module"},
                {"id": "out", "col": 4, "row": 0, "label": "输出\nH×W×K", "kind": "data"},
            ],
            "edges": [{"from": "in", "to": "enc"}, {"from": "enc", "to": "btn"},
                      {"from": "btn", "to": "dec"}, {"from": "dec", "to": "out"}],
            "zoom": {
                "source": "enc", "title": "Encoder block",
                "rect": [0.18, 0.02, 0.64, 0.40],
                "nodes": [
                    {"id": "z1", "col": 0, "row": 0, "label": "Conv 3×3", "kind": "module"},
                    {"id": "z2", "col": 1, "row": 0, "label": "BN + ReLU", "kind": "module"},
                    {"id": "z3", "col": 2, "row": 0, "label": "通道注意力", "kind": "ours"},
                    {"id": "z4", "col": 3, "row": 0, "label": "残差相加", "kind": "op"},
                ],
                "edges": [{"from": "z1", "to": "z2"}, {"from": "z2", "to": "z3"},
                          {"from": "z3", "to": "z4"}],
            },
            "caption": "图 2 编码器由卷积、归一化、通道注意力与残差组成（C-02）。"
                       "放大框只画一个 block，其余 block 用省略号表示；颜色只区分本文模块与通用模块。",
        },
        {
            "id": "A3", "claim": "C-03", "direction": "vertical",
            "width": 3.2, "height": 6.0,
            "area": [0.10, 0.05, 0.80, 0.90],
            "nodes": [
                {"id": "in", "col": 0, "row": 0, "label": "输入 x", "kind": "data"},
                {"id": "mha", "col": 1, "row": 0, "label": "Multi-Head\nAttention", "kind": "module"},
                {"id": "an1", "col": 2, "row": 0, "label": "Add & Norm", "kind": "loss"},
                {"id": "ffn", "col": 3, "row": 0, "label": "Feed Forward", "kind": "module"},
                {"id": "an2", "col": 4, "row": 0, "label": "Add & Norm", "kind": "loss"},
                {"id": "out", "col": 5, "row": 0, "label": "输出", "kind": "data"},
            ],
            "edges": [
                {"from": "in", "to": "mha"}, {"from": "mha", "to": "an1"},
                {"from": "an1", "to": "ffn"}, {"from": "ffn", "to": "an2"},
                {"from": "an2", "to": "out"},
                {"from": "in", "to": "an1", "route": "side", "style": "--"},
                {"from": "an1", "to": "an2", "route": "side", "style": "--"},
            ],
            "annotations": [{"text": "N×", "x": 0.05, "y": 0.5, "fontsize": 10}],
            "caption": "图 3 单个 Transformer block 的竖排画法（C-03）。"
                       "主链自上而下，残差用右侧虚线旁路；N× 表示重复，不把每一层都画出来。",
        },
    ]
    out.mkdir(parents=True, exist_ok=True)
    for s in specs:
        issues = lint(s)
        files = render(s, out / s["id"])
        (out / f"{s['id']}.json").write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{s['id']}: {', '.join(str(f) for f in files)}"
              + (f" | lint: {issues}" if issues else " | lint ok"))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("render")
    p.add_argument("--spec", required=True)
    p.add_argument("--out", default="figures/arch")
    p = sub.add_parser("lint")
    p.add_argument("--spec", required=True)
    p = sub.add_parser("demo")
    p.add_argument("--out", default="figures/arch")
    args = ap.parse_args()

    if args.cmd == "demo":
        demo(Path(args.out))
        return
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    if args.cmd == "lint":
        issues = lint(spec)
        print("\n".join(issues) if issues else "ok")
    else:
        print(render(spec, Path(args.out) / spec["id"]))


if __name__ == "__main__":
    main()
