"""精美小模板库：按 MATLAB 的基础图表语法做可复用面板。

用法：
  py tools/paneltemplates.py list
  py tools/paneltemplates.py demo --out figures/repro/templates_contact.png
  py tools/paneltemplates.py render --name line_ci --out figures/repro/tpl_line.png

设计：
- 颜色用 MATLAB 默认顺序（蓝/橙/黄/紫/绿/青/暗红）；
- 坐标轴：去上右边框、刻度朝外、浅色水平网格；
- 能直接标注就不做图例；关键数值标在端点/柱顶；
- 每个模板只负责一个面板，0—1 坐标，可被拼装器调用。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle  # noqa: E402

PALETTE = ["#0072BD", "#D95319", "#EDB120", "#7E2F8E", "#77AC30", "#4DBEEE", "#A2142F"]
INK = "#333333"
GRID = "#E6E6E6"
REG = {}


def tpl(name):
    def deco(fn):
        REG[name] = fn
        return fn
    return deco


def style(ax, grid_axis="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#555555")
        ax.spines[s].set_linewidth(0.8)
    ax.tick_params(direction="out", length=3, width=0.8, labelsize=7, colors=INK)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)


@tpl("line_ci")
def line_ci(ax, seed=0):
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 10, 32)
    for i, (base, slope) in enumerate([(0.55, 0.055), (0.45, 0.035)]):
        y = base + slope * x + 0.03 * np.sin(x) + rng.normal(0, 0.006, x.size)
        ci = 0.02 + 0.004 * x
        ax.fill_between(x, y - ci, y + ci, color=PALETTE[i], alpha=0.16, lw=0)
        ax.plot(x, y, color=PALETTE[i], lw=1.5)
        ax.text(x[-1] + 0.15, y[-1], f"$\\it{{S}}_{i+1}$", color=PALETTE[i],
                fontsize=8, va="center")
    ax.set_xlim(0, 11)
    ax.set_xlabel("Time (a.u.)", fontsize=8)
    ax.set_ylabel("Score", fontsize=8)
    style(ax)


@tpl("bar_group")
def bar_group(ax, seed=0):
    cats = ["A", "B", "C", "D", "E"]
    a = np.array([0.72, 0.68, 0.75, 0.70, 0.66])
    b = np.array([0.66, 0.62, 0.70, 0.64, 0.61])
    x = np.arange(len(cats))
    w = 0.34
    ax.bar(x - w / 2, a, w, color=PALETTE[0], label="Ours")
    ax.bar(x + w / 2, b, w, color=PALETTE[1], label="Baseline")
    for i in range(len(cats)):
        ax.text(x[i] - w / 2, a[i] + 0.01, f"{a[i]:.2f}", ha="center", fontsize=6, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels(cats)
    ax.set_ylim(0, 0.95)
    ax.set_ylabel("Accuracy", fontsize=8)
    ax.legend(frameon=False, fontsize=6, ncol=2, loc="upper right",
              bbox_to_anchor=(1.0, 1.0), borderaxespad=0.2)
    style(ax)


@tpl("scatter_fit")
def scatter_fit(ax, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 10, 45)
    y = 0.5 + 0.075 * x + rng.normal(0, 0.08, x.size)
    ax.scatter(x, y, s=10, color=PALETTE[0], alpha=0.75, edgecolors="none")
    k, b = np.polyfit(x, y, 1)
    xs = np.linspace(0, 10, 20)
    ax.plot(xs, k * xs + b, color=PALETTE[1], lw=1.3)
    r = np.corrcoef(x, y)[0, 1]
    ax.text(0.05, 0.92, f"$r$ = {r:.2f}", transform=ax.transAxes, fontsize=8)
    ax.set_xlabel("Observed", fontsize=8)
    ax.set_ylabel("Predicted", fontsize=8)
    style(ax)


@tpl("heatmap")
def heatmap(ax, seed=0):
    rng = np.random.default_rng(seed)
    m = rng.uniform(0, 1, (6, 6))
    np.fill_diagonal(m, rng.uniform(0.7, 0.95, 6))
    im = ax.imshow(m, cmap="Blues", vmin=0, vmax=1)
    for i in range(6):
        for j in range(6):
            ax.text(j, i, f"{m[i,j]:.2f}", ha="center", va="center", fontsize=5.5,
                    color="white" if m[i, j] > 0.6 else INK)
    ax.set_xticks(range(6))
    ax.set_yticks(range(6))
    ax.set_xticklabels([f"C{i+1}" for i in range(6)], fontsize=4.8)
    ax.set_yticklabels([f"C{i+1}" for i in range(6)], fontsize=5.5)
    ax.tick_params(axis="x", pad=1)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)


@tpl("violin")
def violin(ax, seed=0):
    rng = np.random.default_rng(seed)
    data = [rng.normal(loc, 0.12, 120) for loc in (0.45, 0.55, 0.62, 0.70)]
    parts = ax.violinplot(data, showextrema=False, widths=0.75)
    for i, body in enumerate(parts["bodies"]):
        body.set_facecolor(PALETTE[i])
        body.set_edgecolor(PALETTE[i])
        body.set_alpha(0.55)
    ax.boxplot(data, widths=0.12, showfliers=False, medianprops=dict(color=INK, lw=1))
    ax.set_xticks(range(1, 5))
    ax.set_xticklabels(["G1", "G2", "G3", "G4"])
    ax.set_ylabel("Value", fontsize=8)
    style(ax)


@tpl("contour")
def contour(ax, seed=0):
    x = np.linspace(-3, 3, 120)
    y = np.linspace(-3, 3, 120)
    X, Y = np.meshgrid(x, y)
    Z = np.exp(-(X ** 2 + Y ** 2)) + 0.5 * np.exp(-((X - 1.5) ** 2 + (Y + 1) ** 2) / 0.5)
    ax.contourf(X, Y, Z, levels=12, cmap="viridis")
    ax.contour(X, Y, Z, levels=6, colors="white", linewidths=0.4, alpha=0.7)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


@tpl("quiver")
def quiver(ax, seed=0):
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 1, 18)
    y = np.linspace(0, 1, 12)
    X, Y = np.meshgrid(x, y)
    U = np.sin(2 * np.pi * Y) + rng.normal(0, 0.08, X.shape)
    V = np.cos(2 * np.pi * X) + rng.normal(0, 0.08, X.shape)
    ax.quiver(X, Y, U, V, color=PALETTE[3], scale=22, width=0.005)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


@tpl("cnn")
def cnn(ax, seed=0):
    labels = ["Conv", "Norm", "Attention", "Add", "FFN", "Add", "Pool"]
    h, gap = 0.095, 0.035
    y = 0.06
    cs = []
    for i, lab in enumerate(labels):
        fill = ["#D6EEF5", "#E7F4E4", "#FBE3C8", "#E7F4E4", "#FBE3C8", "#E7F4E4", "#F7D9E0"][i]
        ax.add_patch(FancyBboxPatch((0.28, y), 0.44, h, boxstyle="round,pad=0.004,rounding_size=0.015",
                                    facecolor=fill, edgecolor="#666666", lw=0.7))
        ax.text(0.50, y + h / 2, lab, ha="center", va="center", fontsize=7)
        cs.append(y + h / 2)
        y += h + gap
    for i in range(len(labels) - 1):
        ax.add_patch(FancyArrowPatch((0.50, cs[i] + h / 2), (0.50, cs[i + 1] - h / 2),
                                     arrowstyle="-|>", mutation_scale=7, color=INK, lw=0.7))
    ax.text(0.20, (cs[2] + cs[4]) / 2, "N×", fontsize=8)
    ax.axis("off")


@tpl("pipeline")
def pipeline(ax, seed=0):
    labels = ["In", "Enc", "Fuse", "Dec", "Out"]
    colors = ["#D6EEF5", "#E7F4E4", "#FBE3C8", "#E7F4E4", "#F7D9E0"]
    w, gap = 0.16, 0.045
    x = 0.02
    cs = []
    for i, lab in enumerate(labels):
        ax.add_patch(FancyBboxPatch((x, 0.40), w, 0.22, boxstyle="round,pad=0.005,rounding_size=0.02",
                                    facecolor=colors[i], edgecolor="#666666", lw=0.8))
        ax.text(x + w / 2, 0.51, lab, ha="center", va="center", fontsize=6.5)
        cs.append(x + w)
        x += w + gap
    for i in range(len(labels) - 1):
        ax.add_patch(FancyArrowPatch((cs[i], 0.50), (cs[i] + gap - 0.005, 0.50),
                                     arrowstyle="-|>", mutation_scale=8, color=INK, lw=0.9))
    ax.axis("off")


@tpl("qualitative")
def qualitative(ax, seed=0):
    rng = np.random.default_rng(seed)
    rows, cols = 3, 4
    for r in range(rows):
        for c in range(cols):
            x = c / cols
            y = 1 - (r + 1) / rows
            # 合成“图像块”：平滑纹理 + 一个亮斑，避免纯噪声
            yy, xx = np.mgrid[0:32, 0:32]
            base = 0.45 + 0.18 * np.sin(xx / 5 + c) + 0.18 * np.cos(yy / 6 + r)
            base += 0.25 * np.exp(-(((xx - 16) ** 2 + (yy - 16) ** 2) / 60))
            tile = np.clip(np.stack([base * 0.75, base * 0.95, base], -1)
                           + rng.normal(0, 0.03, (32, 32, 3)), 0, 1)
            ax.imshow(tile, extent=[x + 0.01, x + 1 / cols - 0.01, y + 0.01, y + 1 / rows - 0.01],
                      aspect="auto", zorder=1)
            ax.add_patch(Rectangle((x + 0.25 / cols, y + 0.20 / rows), 0.5 / cols, 0.5 / rows,
                                   fill=False, edgecolor="#E84A5F", lw=0.9, ls="--", zorder=3))
            if r == 0:
                ax.text(x + 0.5 / cols, 0.982, ["Image", "Ours", "Baseline", "GT"][c],
                        ha="center", va="bottom", fontsize=5.2)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")


def render(name: str, out: Path, size=(3.2, 2.6)) -> Path:
    fig, ax = plt.subplots(figsize=size)
    ax.set_xlim(0, 1) if name in ("pipeline", "qualitative") else None
    ax.set_ylim(0, 1) if name in ("pipeline", "qualitative") else None
    REG[name](ax)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    return out


def demo(out: Path) -> None:
    names = list(REG)
    cols = 4
    rows = (len(names) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(11, 2.9 * rows))
    fig.subplots_adjust(hspace=0.55, wspace=0.28, top=0.94, bottom=0.05)
    for ax, name in zip(axes.ravel(), names):
        REG[name](ax)
        ax.set_title(name, fontsize=9, loc="left", pad=6)
    for ax in axes.ravel()[len(names):]:
        ax.axis("off")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=220, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p = sub.add_parser("demo")
    p.add_argument("--out", default="figures/repro/templates_contact.png")
    p = sub.add_parser("render")
    p.add_argument("--name", required=True)
    p.add_argument("--out", default="figures/repro/tpl.png")
    args = ap.parse_args()

    if args.cmd == "list":
        for k in REG:
            print(k)
    elif args.cmd == "demo":
        demo(Path(args.out))
        print(args.out)
    else:
        print(render(args.name, Path(args.out)))


if __name__ == "__main__":
    main()
