"""双高论文的研究框架图：三层架构 + 关键增量 + 配额小图（复合图）。"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch  # noqa: E402

plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "font.size": 6.4,
    "axes.linewidth": 0.6,
    "pdf.fonttype": 42,
})
INK = "#222222"
BLUE = "#2F6DB3"
GREEN = "#5A9E5A"
ORANGE = "#D9772B"
GREY = "#8C8C8C"
OUT = Path("projects/双高2026/figures/fig2_framework.png")


def box(ax, x, y, w, h, title, lines, color, fill="#FFFFFF"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.35,rounding_size=1.2",
                                facecolor=fill, edgecolor=color, lw=1.0, zorder=2))
    ax.text(x + w / 2, y + h * 0.64, title, ha="center", va="center", fontsize=6.6,
            fontweight="bold", color=INK, zorder=3)
    for i, ln in enumerate(lines):
        ax.text(x + w / 2, y + h * 0.36 - i * 2.8, ln, ha="center", va="center",
                fontsize=5.7, color="#444444", zorder=3)


def arrow(ax, p1, p2, color="#777777", lw=0.8):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=6,
                                 color=color, lw=lw, zorder=1, shrinkA=0, shrinkB=0))


def band(ax, y, h, label, color):
    ax.add_patch(FancyBboxPatch((2, y), 96, h, boxstyle="round,pad=0.2,rounding_size=2",
                                facecolor="#FAFBFD", edgecolor="#E3E7EE", lw=0.6, zorder=0))
    ax.add_patch(Circle((4.6, y + h - 2.4), 1.5, facecolor=color, edgecolor="none", zorder=4))
    ax.text(4.6, y + h - 2.4, label, ha="center", va="center", fontsize=6.2,
            color="white", fontweight="bold", zorder=5)


def main():
    fig = plt.figure(figsize=(7.4, 4.8))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    band(ax, 67, 31, "a", BLUE)
    band(ax, 35, 30, "b", GREEN)
    band(ax, 3, 30, "c", ORANGE)
    ax.text(7, 95.2, "数据与预处理", fontsize=7.0, color=BLUE, fontweight="bold")
    ax.text(7, 63.2, "模型与集成", fontsize=7.0, color=GREEN, fontweight="bold")
    ax.text(7, 31.2, "推理与后处理", fontsize=7.0, color=ORANGE, fontweight="bold")

    # 数据层
    box(ax, 7, 73, 19, 15, "42 个日期", ["130803 占 26%", "8 类单日期监督"], BLUE)
    box(ax, 30, 73, 19, 15, "41 张重叠", ["交集 12.26%", "查表 +0.0238"], BLUE)
    box(ax, 53, 73, 19, 15, "双表示", ["224→346→173", "谱形 + 全局统计"], BLUE)
    box(ax, 76, 73, 19, 15, "五套归一化", ["全局 +0.0282", "口径随权重保存"], BLUE)
    for x in (26.2, 49.2, 72.2):
        arrow(ax, (x, 80.5), (x + 3.6, 80.5), BLUE)

    # 模型层
    box(ax, 7, 43, 18, 13, "R34-U-Net", ["7 成员", "21—24M"], GREEN)
    box(ax, 27, 43, 18, 13, "EfficientNet", ["2 成员", "约 19M"], GREEN)
    box(ax, 47, 43, 18, 13, "SN-MSU", ["8 成员", "5—12M"], GREEN)
    box(ax, 67, 43, 15, 13, "小模型", ["77 MB"], GREEN)
    for x in (25.2, 45.2, 65.2):
        arrow(ax, (x, 49.5), (x + 1.6, 49.5), GREEN)
    ax.add_patch(Circle((91, 49.5), 4.2, facecolor="#E8F0E8", edgecolor=GREEN, lw=0.9, zorder=2))
    ax.text(91, 50.6, "融合", ha="center", va="center", fontsize=6.0, fontweight="bold")
    ax.text(91, 47.8, "0.40/0.60", ha="center", va="center", fontsize=5.6)
    ax.text(55, 38.0, "跨族 +0.0107 / 同族 +0.0009", fontsize=5.4, color="#666666")

    # 推理层
    steps = [
        ("9 窗 + 7 TTA", "+0.0004"), ("BN 重标定", "OA −0.0250"),
        ("空间平滑", "21×21"), ("分位 35%", "16.4M px"), ("类 32 注入", "+0.0182"),
    ]
    for i, (name, sub) in enumerate(steps):
        x = 6 + i * 17
        box(ax, x, 12, 14, 11, name, [sub], ORANGE)
        if i < 4:
            arrow(ax, (x + 14.3, 17.5), (x + 16.7, 17.5), ORANGE)

    # 层间箭头
    arrow(ax, (85, 72.5), (85, 65.5), GREY, 1.0)
    ax.text(86, 68.4, "+0.0282", fontsize=5.4, color=GREY)
    arrow(ax, (95.5, 42.5), (95.5, 33.5), GREY, 1.0)
    ax.text(88.0, 37.2, "+0.0182", fontsize=5.4, color=GREY)

    fig.savefig(OUT, dpi=400, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
