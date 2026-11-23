"""SN-MSU 架构图：谱原生 stem + /1—/8 编码 + /16 半宽 + U-Net 解码 + DRB/SARA。"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "font.size": 6,
    "axes.linewidth": 0.6,
    "pdf.fonttype": 42,
})
INK = "#222222"
BLUE = "#2F6DB3"
PURPLE = "#7E5AA8"
ORANGE = "#D9772B"
GREEN = "#5A9E5A"
RED = "#B03A2E"
GREY = "#8C8C8C"
OUT = Path("projects/双高2026/figures/fig5_snmsu.png")


def box(ax, x, y, w, h, text, color, fill="white", fs=6.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=0.8",
                                facecolor=fill, edgecolor=color, lw=1.0, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=INK, zorder=3, linespacing=1.35)


def arrow(ax, p1, p2, color="#777777", lw=0.8, ls="-"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=6,
                                 color=color, lw=lw, ls=ls, shrinkA=0, shrinkB=0, zorder=1))


def main():
    fig = plt.figure(figsize=(7.4, 4.2))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # 输入与 stem
    box(ax, 1.5, 86, 10, 7, "dual 输入\n346×512×512", GREY, "#F4F4F4", 5.6)
    box(ax, 14, 86, 15, 7, "1×1 谱原生 stem\n346→128", PURPLE, "white", 5.8)
    arrow(ax, (11.7, 89.5), (13.8, 89.5), GREY)

    # 编码器
    enc = [
        (74, "s1  128  /1", BLUE),
        (61, "s2  256  /2", BLUE),
        (48, "s3  512  /4", BLUE),
        (35, "s4  896  /8\nDRB K=7", ORANGE),
        (22, "s5  448  /16\nSARA", GREEN),
    ]
    for y, text, color in enc:
        box(ax, 14, y, 15, 7, text, color, "white", 5.8)
    arrow(ax, (21.5, 86), (21.5, 81.2), GREY)
    for y in (74, 61, 48, 35):
        arrow(ax, (21.5, y), (21.5, y - 5.8), GREY)

    # 解码器
    dec = [
        (35, "u4  896\ncat e5+e4", BLUE),
        (48, "u3  512\ncat e3", BLUE),
        (61, "u2  256\ncat e2", BLUE),
        (74, "u1  128\ncat e1", BLUE),
    ]
    for y, text, color in dec:
        box(ax, 60, y, 15, 7, text, color, "white", 5.8)
    for y in (35, 48, 61):
        arrow(ax, (67.5, y + 7), (67.5, y + 12.8), "#444444")

    # skip
    for ye, yu in ((74, 74), (61, 61), (48, 48), (35, 35)):
        arrow(ax, (29.2, ye + 3.5), (59.7, yu + 3.5), GREY, 0.7, (0, (3, 2)))
    arrow(ax, (29.2, 25.5), (59.7, 37.0), GREY, 0.7, (0, (3, 2)))
    ax.text(44, 27.0, "e5 → u4", fontsize=5.0, color="#777777", ha="center")

    # 头
    box(ax, 80, 74, 13, 7, "1×1 头\n31 类", RED, "white", 5.8)
    arrow(ax, (75.2, 77.5), (79.7, 77.5), "#444444")
    ax.text(94.5, 77.5, "logits", fontsize=5.2, va="center", ha="left")

    # 模块说明
    box(ax, 4, 3, 27, 13, "", ORANGE, "#FFF8F0", 5.4)
    ax.text(17.5, 13.2, "DRB（/8）", ha="center", fontsize=6.0, fontweight="bold", color=ORANGE)
    ax.text(17.5, 9.4, "K=7 多膨胀并行（1/2/3/4）", ha="center", fontsize=5.0)
    ax.text(17.5, 6.2, "推理折叠成等效 7×7 depthwise", ha="center", fontsize=5.0)
    ax.text(17.5, 3.6, "ERF ≈ 60 px", ha="center", fontsize=5.2, color=ORANGE)

    box(ax, 34, 3, 30, 13, "", GREEN, "#F2FAF2", 5.4)
    ax.text(49, 13.2, "SARA（/16）", ha="center", fontsize=6.0, fontweight="bold", color=GREEN)
    ax.text(49, 9.4, "q/k/v → softmax 亲和 → 迭代 2 次", ha="center", fontsize=5.0)
    ax.text(49, 6.2, "零初始化门控；4 MB/样本", ha="center", fontsize=5.0)
    ax.text(49, 3.6, "唯一的内容相关算子", ha="center", fontsize=5.0, color=GREEN)

    box(ax, 67, 3, 29, 13, "", GREY, "#FAFAFA", 5.4)
    ax.text(81.5, 13.2, "规格", ha="center", fontsize=6.0, fontweight="bold", color=INK)
    ax.text(81.5, 9.6, "参数 5,015,711", ha="center", fontsize=5.2)
    ax.text(81.5, 6.4, "通道 128/256/512/896", ha="center", fontsize=5.0)
    ax.text(81.5, 3.7, "上采样 nearest；/16 半宽 448", ha="center", fontsize=4.8)

    fig.savefig(OUT, dpi=400, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
