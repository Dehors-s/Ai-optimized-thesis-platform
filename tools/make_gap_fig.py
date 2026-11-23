"""画“我们 vs 本地顶刊语料”的图表差距：参考文献/图/表 + 图型分布。"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "font.size": 7,
    "axes.linewidth": 0.6,
    "pdf.fonttype": 42,
})
BLUE = "#2F6DB3"
ORANGE = "#D9772B"
GREY = "#BDBDBD"
OUT = Path("projects/双高2026/figures/gap_dashboard.png")


def style(ax, grid="x"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#555555")
        ax.spines[s].set_linewidth(0.6)
    ax.tick_params(direction="out", length=2.2, width=0.6)
    if grid:
        ax.grid(axis=grid, color="#E9E9E9", lw=0.55)
        ax.set_axisbelow(True)


def main():
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 3.0),
                               gridspec_kw={"width_ratios": [1, 1.25]})
    fig.subplots_adjust(wspace=0.42, left=0.19, right=0.97, top=0.82, bottom=0.16)

    # a: 相对本地中位数
    labels = ["参考文献", "图", "表"]
    corpus = [33.5, 8.5, 3.0]
    ours = [6, 6, 8]
    rel = [o / c * 100 for o, c in zip(ours, corpus)]
    y = np.arange(3)
    a.barh(y, [100] * 3, height=0.50, color="#E6E6E6", edgecolor="none")
    a.barh(y, rel, height=0.50, color=[ORANGE if r < 80 or r > 160 else BLUE for r in rel],
           edgecolor="none")
    for i, (r, o, c) in enumerate(zip(rel, ours, corpus)):
        a.text(min(r + 4, 285), i, f"{o} / 中位 {c:g}（{r:.0f}%）", va="center", fontsize=5.8)
    a.axvline(100, color="#777777", lw=0.7, ls=":")
    a.set_yticks(y)
    a.set_yticklabels(labels)
    a.set_xlim(0, 305)
    a.set_xlabel("相对本地论文中位数（%）")
    a.set_title("篇幅与引用", fontsize=7.4, pad=5)
    style(a, "x")

    # b: 图型分布
    types = ["架构", "地图", "分布", "定性", "散点", "其他"]
    corpus_pct = [29, 25, 14, 13, 7, 12]
    ours_pct = [17, 0, 83, 0, 0, 0]
    y = np.arange(len(types))[::-1]
    b.barh(y + 0.18, corpus_pct, height=0.32, color=GREY, label="本地语料（196 张）")
    b.barh(y - 0.18, ours_pct, height=0.32, color=ORANGE, label="本文（6 张）")
    for i, v in enumerate(corpus_pct):
        b.text(v + 1.2, y[i] + 0.18, f"{v}%", va="center", fontsize=5.6, color="#555555")
    for i, v in enumerate(ours_pct):
        b.text(v + 1.2, y[i] - 0.18, f"{v}%", va="center", fontsize=5.6, color=ORANGE)
    b.set_yticks(y)
    b.set_yticklabels(types)
    b.set_xlim(0, 92)
    b.set_xlabel("占比（%）")
    b.set_title("图型分布", fontsize=7.4, pad=5)
    b.legend(frameon=False, fontsize=5.6, loc="lower right", handlelength=1.0)
    style(b, "x")

    fig.savefig(OUT, dpi=400, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
