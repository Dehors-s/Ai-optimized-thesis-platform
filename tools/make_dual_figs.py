"""双高论文插图：按 docs/25 的画像重做（少墨、直接标注、面板字母、统一配色）。"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon  # noqa: E402

plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "font.size": 7,
    "axes.labelsize": 7.2,
    "xtick.labelsize": 6.6,
    "ytick.labelsize": 6.6,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})
INK = "#222222"
GREY = "#8C8C8C"
LGREY = "#D9D9D9"
GRID = "#E9E9E9"
BLUE = "#2F6DB3"
LBLUE = "#A8C4E0"
ORANGE = "#D9772B"
GREEN = "#5A9E5A"
OUT = Path("projects/双高2026/figures")


def style(ax, grid="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#555555")
        ax.spines[s].set_linewidth(0.6)
    ax.tick_params(direction="out", length=2.2, width=0.6, colors=INK, pad=1.5)
    if grid:
        ax.grid(axis=grid, color=GRID, lw=0.55)
        ax.set_axisbelow(True)


def plabel(ax, s):
    ax.text(-0.14, 1.06, s, transform=ax.transAxes, fontsize=8,
            fontweight="bold", va="bottom", ha="left")


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=400, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


# ---------------- 图 1 七阶段 ----------------
def fig1():
    fig = plt.figure(figsize=(7.2, 2.05))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    stages = [
        ("1", "数据挖潜", "+0.0730", "data"),
        ("2", "归一化", "+0.0282", "data"),
        ("3", "模型族", "4 族 17 成员", "model"),
        ("4", "推理解码", "+0.0004", "post"),
        ("5", "后处理", "+0.0008", "post"),
        ("6", "开集配额", "+0.0182", "post"),
        ("7", "出包校验", "7 项", "gate"),
    ]
    colors = {"data": BLUE, "model": GREEN, "post": ORANGE, "gate": GREY}
    w, gap = 0.120, 0.020
    x = 0.012
    centers = []
    for num, name, delta, kind in stages:
        y, h = 0.34, 0.36
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.010",
                                    facecolor="white", edgecolor=colors[kind], lw=1.0))
        ax.text(x + 0.017, y + h - 0.055, num, ha="center", va="center",
                fontsize=5.2, color="white", fontweight="bold",
                bbox=dict(boxstyle="circle,pad=0.18", facecolor=colors[kind],
                          edgecolor="none"))
        ax.text(x + w / 2, y + 0.20, name, ha="center", va="center", fontsize=6.6,
                fontweight="bold", color=INK)
        ax.text(x + w / 2, y + 0.09, delta, ha="center", va="center", fontsize=6.0,
                color=colors[kind])
        centers.append((x, x + w, y + h / 2))
        x += w + gap
    for i in range(len(centers) - 1):
        ax.add_patch(FancyArrowPatch((centers[i][1] + 0.002, centers[i][2]),
                                     (centers[i + 1][0] - 0.002, centers[i + 1][2]),
                                     arrowstyle="-|>", mutation_scale=5.5,
                                     lw=0.6, color="#777777"))
    # 阶段括号
    brackets = [(0.012, 0.252, "数据与预处理", BLUE),
                (0.272, 0.392, "模型", GREEN),
                (0.412, 0.812, "推理与后处理", ORANGE),
                (0.832, 0.972, "闸门", GREY)]
    for x0, x1, text, color in brackets:
        y = 0.80
        ax.plot([x0, x0, x1, x1], [y, y + 0.03, y + 0.03, y], color=color, lw=0.7)
        ax.text((x0 + x1) / 2, y + 0.055, text, ha="center", va="bottom",
                fontsize=6.2, color=color)
    ax.text(0.012, 0.15, "注：数字为线上实测增量，含 ±0.0061 噪声，阶段间不可相加。",
            fontsize=5.8, color="#666666")
    save(fig, "fig1_pipeline.png")


# ---------------- 图 2 数据与漏斗 ----------------
def fig2():
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 2.6),
                               gridspec_kw={"width_ratios": [1.05, 1]})
    fig.subplots_adjust(wspace=0.42, left=0.11, right=0.97, top=0.84, bottom=0.14)
    labels = ["接触", "远离", "重叠", "新航线"]
    vals = [67, 43, 41, 28]
    colors = [LBLUE, LBLUE, ORANGE, LBLUE]
    y = np.arange(len(vals))[::-1]
    a.barh(y, vals, height=0.58, color=colors, edgecolor="none")
    for yy, v in zip(y, vals):
        a.text(v + 1.5, yy, f"{v}（{v/179:.0%}）", va="center", fontsize=6.2)
    a.set_yticks(y)
    a.set_yticklabels(labels)
    a.set_xlim(0, 88)
    a.set_xlabel("测试瓦片数")
    a.set_title("测试集构成", fontsize=7.2, pad=4)
    style(a, grid="x")
    plabel(a, "a")

    b.set_xlim(0, 1)
    b.set_ylim(0, 1)
    b.axis("off")
    b.set_title("重叠区查表漏斗", fontsize=7.2, pad=4)
    rows = [
        ("训练∩测试交集", "5,751,828", "12.26%", 0.88, BLUE),
        ("其中带标注", "1,730,439", "3.69%", 0.72, "#6C97C8"),
        ("实际改写", "371,388", "0.79%", 0.56, ORANGE),
    ]
    for i, (name, n, pct, w, color) in enumerate(rows):
        y0 = 0.66 - i * 0.22
        cx = 0.50
        w2 = w - 0.06
        b.add_patch(Polygon([[cx - w / 2, y0 + 0.075], [cx + w / 2, y0 + 0.075],
                             [cx + w2 / 2, y0 - 0.075], [cx - w2 / 2, y0 - 0.075]],
                            closed=True, facecolor=color, edgecolor="none", alpha=0.92))
        b.text(cx, y0 + 0.035, name, ha="center", va="center", fontsize=5.6,
               color="white" if i < 2 else "white")
        b.text(cx, y0 - 0.035, f"{n}  ({pct})", ha="center", va="center",
               fontsize=6.0, color="white", fontweight="bold")
    b.text(0.5, 0.03, "交集大、有标注少、真正改写不到 1%", ha="center",
           fontsize=5.6, color="#666666")
    plabel(b, "b")
    save(fig, "fig1_data.png")


# ---------------- 图 3 增量与噪声 ----------------
def fig3():
    fig, ax = plt.subplots(figsize=(4.1, 2.7))
    fig.subplots_adjust(left=0.30, right=0.96, top=0.90, bottom=0.16)
    items = [
        ("2×2 拼接", 0.0730), ("全局归一化", 0.0282), ("重叠查表", 0.0238),
        ("开集配额", 0.0182), ("跨族融合", 0.0127), ("近缘对精修", 0.0008),
        ("9 窗 + 7 TTA", 0.0004),
    ]
    items = sorted(items, key=lambda t: t[1])
    ys = np.arange(len(items))
    vals = [v for _, v in items]
    ax.axvspan(-0.0061, 0.0061, color="#E5E5E5", lw=0, zorder=0)
    ax.axvline(0.015, color=ORANGE, ls=(0, (4, 2)), lw=0.8, zorder=1)
    ax.hlines(ys, 0, vals, color=LGREY, lw=0.8, zorder=2)
    ax.scatter(vals, ys, s=18, color=BLUE, zorder=3)
    for y, v in zip(ys, vals):
        ax.text(v + 0.0018, y, f"{v:+.4f}", va="center", fontsize=5.6, color=INK)
    ax.set_yticks(ys)
    ax.set_yticklabels([n for n, _ in items], fontsize=6.2)
    ax.set_xlim(-0.008, 0.080)
    ax.set_xlabel("线上 ΔF1")
    ax.text(0.0152, len(items) - 0.35, "0.015", fontsize=5.4, color=ORANGE)
    ax.text(0.0005, len(items) - 0.35, "噪声带", fontsize=5.4, color="#666666")
    style(ax, grid="x")
    plabel(ax, "a")
    save(fig, "fig3_probe.png")


# ---------------- 图 4 开集判据与配额 ----------------
def fig4():
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 2.7),
                               gridspec_kw={"width_ratios": [1, 1.15]})
    fig.subplots_adjust(wspace=0.42, left=0.13, right=0.97, top=0.84, bottom=0.15)
    crit = ["最大概率", "熵", "间隔"]
    unsup = [0.5276, 0.5479, 0.5084]
    sup = [0.7790, 0.7394, 0.7224]
    y = np.arange(3)
    for i in range(3):
        a.hlines(y[i], unsup[i], sup[i], color=LGREY, lw=1.0, zorder=1)
        a.scatter(unsup[i], y[i], s=20, color="#BDBDBD", zorder=3, label="无监督" if i == 0 else None)
        a.scatter(sup[i], y[i], s=20, color=BLUE, zorder=3, label="有监督对照" if i == 0 else None)
        a.text(unsup[i] - 0.007, y[i] + 0.14, f"{unsup[i]:.3f}", ha="right",
               fontsize=5.6, color="#666666")
        a.text(sup[i] + 0.007, y[i] + 0.14, f"{sup[i]:.3f}", fontsize=5.6, color=BLUE)
    a.axvline(0.5, color=GREY, lw=0.6, ls=":")
    a.text(0.505, 2.55, "0.5 随机", fontsize=5.2, color=GREY)
    a.set_yticks(y)
    a.set_yticklabels(crit)
    a.set_xlim(0.46, 0.85)
    a.set_ylim(-0.4, 2.75)
    a.set_xlabel("AUC")
    a.legend(frameon=False, fontsize=5.4, loc="upper center", bbox_to_anchor=(0.5, -0.28),
             ncol=2, handletextpad=0.3, columnspacing=1.2)
    a.set_title("判据可分性", fontsize=7.2, pad=6)
    style(a, grid="x")
    plabel(a, "a")

    q = [4.52, 18, 20, 25, 30, 35]
    f1 = [0.6394, 0.6436, 0.6460, 0.6522, 0.6557, 0.6558]
    b.axvspan(30, 35, color="#F4E3C8", lw=0, zorder=0)
    b.plot(q, f1, "-o", color=BLUE, ms=2.8, lw=1.0, zorder=3)
    for x, yv in zip(q, f1):
        if x in (4.52, 20, 25, 35):
            b.text(x, yv + 0.0012, f"{yv:.4f}", ha="center", fontsize=5.4)
    b.set_xlim(0, 40)
    b.set_ylim(0.6375, 0.6585)
    b.set_xlabel("判为第 32 类的比例（%）")
    b.set_ylabel("宏平均 F1")
    b.set_title("配额剂量", fontsize=7.2, pad=4)
    b.text(32.5, 0.6382, "平台", ha="center", fontsize=5.4, color="#8A6D3B")
    style(b, grid="y")
    plabel(b, "b")
    save(fig, "fig6_openset.png")


# ---------------- 图 5 平台与分数构成 ----------------
def fig5():
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 2.6),
                               gridspec_kw={"width_ratios": [1, 1]})
    fig.subplots_adjust(wspace=0.42, left=0.13, right=0.96, top=0.84, bottom=0.17)
    win = [5, 9, 17, 21, 25]
    val = [0.6578, 0.6579, 0.6583, 0.6584, 0.6583]
    a.axhspan(0.6578 - 0.0061, 0.6578 + 0.0061, color="#EDEDED", lw=0)
    a.plot(win, val, "-o", color=BLUE, ms=2.8, lw=1.0, zorder=3)
    a.set_xlim(3, 27)
    a.set_ylim(0.645, 0.672)
    a.set_xlabel("平滑窗宽")
    a.set_ylabel("宏平均 F1")
    a.set_title("窗宽扫描", fontsize=7.2, pad=4)
    a.annotate("落差 0.0006 < 噪声 0.0061", xy=(21, 0.6584), xytext=(7, 0.666),
               fontsize=5.6, color="#666666",
               arrowprops=dict(arrowstyle="-", lw=0.5, color="#999999"))
    style(a, grid="y")
    plabel(a, "a")

    b.set_xlim(-0.5, 2.5)
    b.set_ylim(0.60, 0.675)
    b.bar([0], [0.6376 - 0.60], bottom=[0.60], width=0.45, color=LBLUE, edgecolor="none")
    b.bar([1], [0.0182], bottom=[0.6376], width=0.45, color=ORANGE, edgecolor="none")
    b.bar([2], [0.6558 - 0.60], bottom=[0.60], width=0.45, color=GREEN, edgecolor="none")
    b.hlines(0.6376, 0.22, 1.22, color=GREY, lw=0.6, ls=(0, (2, 2)))
    b.hlines(0.6558, 0.78, 1.78, color=GREY, lw=0.6, ls=(0, (2, 2)))
    b.text(0, 0.6376 + 0.0015, "0.6376", ha="center", fontsize=5.8)
    b.text(1, 0.6558 + 0.0015, "+0.0182", ha="center", fontsize=5.8, color=ORANGE)
    b.text(2, 0.6558 + 0.0015, "0.6558", ha="center", fontsize=5.8, color=GREEN)
    b.set_xticks([0, 1, 2])
    b.set_xticklabels(["31 类均值", "类 32 项", "阶段总分"], fontsize=6.0)
    b.set_ylabel("宏平均 F1")
    b.set_title("分数构成（可精确相加）", fontsize=7.2, pad=4)
    b.spines["top"].set_visible(False)
    b.spines["right"].set_visible(False)
    b.tick_params(direction="out", length=2.2, width=0.6)
    plabel(b, "b")
    save(fig, "fig8_platform.png")


# ---------------- 图 6 收益来源 ----------------
def fig6():
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 2.2),
                               gridspec_kw={"width_ratios": [1.2, 1]})
    fig.subplots_adjust(wspace=0.38, left=0.10, right=0.97, top=0.80, bottom=0.22)
    a.barh([0], [0.90], height=0.46, color=BLUE, edgecolor="none")
    a.barh([0], [0.10], left=[0.90], height=0.46, color=ORANGE, edgecolor="none")
    a.text(0.45, 0, "≈90%", ha="center", va="center", color="white", fontsize=8)
    a.text(0.95, 0, "≈10%", ha="center", va="center", color="white", fontsize=7)
    a.text(0.45, -0.38, "已知类 F1 清理", ha="center", fontsize=6.0, color=BLUE)
    a.text(0.95, -0.38, "类 32 自身项", ha="center", fontsize=6.0, color=ORANGE)
    a.set_xlim(0, 1)
    a.set_ylim(-0.6, 0.4)
    a.set_yticks([])
    a.set_title("配额 +0.0182 的来源", fontsize=7.2, pad=4)
    a.set_xlabel("占比")
    for s in ("top", "right", "left"):
        a.spines[s].set_visible(False)
    a.tick_params(direction="out", length=2.2, width=0.6)
    plabel(a, "a")

    b.bar([0], [0.0023], width=0.42, color=LGREY, edgecolor="none")
    b.bar([1], [0.0182], width=0.42, color=BLUE, edgecolor="none")
    b.text(0, 0.0023 + 0.0006, "0.0023", ha="center", fontsize=6.0)
    b.text(1, 0.0182 + 0.0006, "0.0182", ha="center", fontsize=6.0)
    b.set_xticks([0, 1])
    b.set_xticklabels(["类 32 上限", "实测净增益"], fontsize=6.0)
    b.set_ylim(0, 0.022)
    b.set_ylabel("对宏平均 F1 的贡献")
    b.set_title("上限与实测", fontsize=7.2, pad=4)
    style(b, grid="y")
    plabel(b, "b")
    save(fig, "fig7_attribution.png")


def main():
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
    fig6()
    print("done")


if __name__ == "__main__":
    main()
