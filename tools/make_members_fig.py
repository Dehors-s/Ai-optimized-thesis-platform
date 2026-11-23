"""F4 成员池架构图：4 族 17 成员 + 融合式 + 异构互补小图。"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle  # noqa: E402

plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "font.size": 6.5,
    "axes.linewidth": 0.6,
    "pdf.fonttype": 42,
})
INK = "#222222"
BLUE = "#2F6DB3"
GREEN = "#5A9E5A"
ORANGE = "#D9772B"
GREY = "#8C8C8C"
OUT = Path("projects/双高2026/figures/fig4_members.png")


def arrow(ax, p1, p2, color="#777777", lw=0.8):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=6,
                                 color=color, lw=lw, shrinkA=0, shrinkB=0, zorder=1))


def main():
    fig = plt.figure(figsize=(7.2, 3.4))
    ax = fig.add_axes([0.01, 0.04, 0.64, 0.90])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    families = [
        ("R34-U-Net", 7, 21, 24, BLUE, "651.1 MB"),
        ("EfficientNet-B4", 2, 19, 19, GREEN, "281.7 MB"),
        ("SN-MSU", 8, 5.05, 12, ORANGE, "172.8 MB"),
    ]
    ys = [0.72, 0.47, 0.22]
    for (name, n, pmin, pmax, color, mb), y in zip(families, ys):
        ax.text(0.02, y + 0.05, name, fontsize=6.8, fontweight="bold", color=INK)
        ax.text(0.02, y - 0.01, f"{n} 成员 · {pmin:g}—{pmax:g}M", fontsize=5.6, color="#555555")
        ax.text(0.02, y - 0.06, mb, fontsize=5.2, color=color)
        x = 0.26
        for i in range(n):
            side = 0.045 + 0.018 * ((pmin + (pmax - pmin) * i / max(n - 1, 1)) - 5) / 19
            ax.add_patch(Rectangle((x, y - side / 2), side, side, facecolor=color,
                                   edgecolor="white", lw=0.4, alpha=0.9, zorder=2))
            x += side + 0.012
        arrow(ax, (x + 0.01, y), (0.79, 0.50), color, 0.9)

    ax.add_patch(Circle((0.86, 0.50), 0.055, facecolor="#F2F2F2", edgecolor=GREY, lw=0.8, zorder=3))
    ax.text(0.86, 0.52, "融合", ha="center", va="center", fontsize=6.0, fontweight="bold")
    ax.text(0.86, 0.475, "0.40/0.60", ha="center", va="center", fontsize=5.4)
    ax.text(0.86, 0.14, "P = 0.40·c4", ha="center", fontsize=5.0, color=INK)
    ax.text(0.86, 0.09, "+ 0.60·(7pos+2c56+2sn4)/11", ha="center", fontsize=4.2, color="#555555")
    arrow(ax, (0.915, 0.50), (0.975, 0.50), GREY, 0.9)
    ax.text(0.965, 0.54, "31 类", fontsize=5.0, ha="left")
    ax.text(0.965, 0.46, "概率", fontsize=5.0, ha="left")
    ax.text(0.02, 0.03, "17 个成员 · 约 1.2 GB · 参数量跨度 5.05—24M（含小模型 77.3 MB）", fontsize=5.2,
            color="#666666")
    ax.text(0.01, 0.98, "a", fontsize=8, fontweight="bold", va="top")

    # 右侧：异构互补
    bx = fig.add_axes([0.70, 0.18, 0.27, 0.55])
    labels = ["跨族", "同族"]
    vals = [0.0107, 0.0009]
    colors = [BLUE, GREY]
    y = np.arange(2)
    bx.barh(y, vals, height=0.42, color=colors, edgecolor="none")
    for i, v in enumerate(vals):
        txt = f"{v:+.4f}" + ("（0.0107—0.0127）" if i == 0 else "")
        bx.text(v + 0.0004, i, txt, va="center", fontsize=5.4)
    bx.set_yticks(y)
    bx.set_yticklabels(labels, fontsize=6.0)
    bx.set_xlim(0, 0.0155)
    bx.set_xlabel("线上 ΔF1", fontsize=5.8)
    bx.set_title("异构互补", fontsize=6.6, pad=3)
    for s in ("top", "right"):
        bx.spines[s].set_visible(False)
    bx.tick_params(direction="out", length=2, width=0.6, labelsize=5.4)
    bx.grid(axis="x", color="#E9E9E9", lw=0.5)
    bx.set_axisbelow(True)
    bx.text(0.0002, -0.55, "同族 ×12 差距", fontsize=5.0, color="#777777")
    bx.text(-0.18, 1.08, "b", transform=bx.transAxes, fontsize=8, fontweight="bold", va="top")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=400, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
