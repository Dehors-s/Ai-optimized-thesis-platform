"""复刻 MTDL 架构图（Nature Communications, PMC13212600 Fig.1）——L1 版式复刻。

六个容器：a 流形表示 / b 向量场 / c Hodge 谱 / d Hodge 分解 / e CNN / f 分类。
数据与图形为合成示意，只复刻布局、配色、流程与标签。

用法：
  py tools/repro_mtdl.py --out figures/repro/MTDL_arch
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import (Circle, FancyArrowPatch, FancyBboxPatch,  # noqa: E402
                                Polygon, Rectangle)

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False

C_A = "#2E9E4F"   # 绿
C_B = "#3B82C4"   # 蓝
C_C = "#E0A800"   # 黄
C_D = "#8E5BB5"   # 紫
C_E = "#2AA7B8"   # 青
C_F = "#2AA7B8"   # 青（f 与 e 同色系）


def container(ax, x, y, w, h, color, letter, title):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.8",
                                fill=False, edgecolor=color, lw=1.8, ls=(0, (5, 3)), zorder=1))
    ax.add_patch(FancyBboxPatch((x + 0.5, y + h - 3.2), 3.2, 2.4,
                                boxstyle="round,pad=0.12,rounding_size=0.35",
                                facecolor=color, edgecolor=color, lw=0.6, zorder=3))
    ax.text(x + 2.1, y + h - 2.0, letter, ha="center", va="center", color="white",
            fontsize=10, fontweight="bold", zorder=4)
    ax.text(x + 4.4, y + h - 2.0, title, ha="left", va="center", fontsize=6.4, zorder=4)


def grid(ax, x, y, w, h, cols=8, rows=8, filled=None, fill="#F2D7A0",
         nodes=False, edge="#D8D8D8"):
    ax.add_patch(Rectangle((x, y), w, h, facecolor="white", edgecolor=edge, lw=0.6, zorder=2))
    for i in range(1, cols):
        ax.plot([x + w * i / cols] * 2, [y, y + h], color=edge, lw=0.35, zorder=2)
    for j in range(1, rows):
        ax.plot([x, x + w], [y + h * j / rows] * 2, color=edge, lw=0.35, zorder=2)
    for (i, j) in (filled or []):
        ax.add_patch(Rectangle((x + w * i / cols, y + h * j / rows),
                               w / cols, h / rows, facecolor=fill, edgecolor="none",
                               alpha=0.9, zorder=2.5))
    if nodes:
        for i in range(cols + 1):
            for j in range(rows + 1):
                if (i, j) in (filled or set()) or (i - 1, j - 1) in (filled or set()):
                    ax.plot(x + w * i / cols, y + h * j / rows, "o", ms=2.2,
                            color="#2E6DA4", zorder=3)


def arrow(ax, p1, p2, color="#666666", lw=2.0, style="-|>"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=9,
                                 color=color, lw=lw, zorder=4, shrinkA=0, shrinkB=0))


def text(ax, x, y, s, fs=6.2, ha="center", va="center", color="#111111", weight="normal"):
    ax.text(x, y, s, ha=ha, va=va, fontsize=fs, color=color, fontweight=weight, zorder=5)


def blob(ax, cx, cy, r, color, seed=0, alpha=0.95):
    rng = np.random.default_rng(seed)
    n = 30
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    rr = r * (1 + 0.12 * rng.normal(size=n))
    pts = np.c_[cx + rr * np.cos(th), cy + rr * np.sin(th)]
    ax.add_patch(Polygon(pts, closed=True, facecolor=color, edgecolor="none",
                         alpha=alpha, zorder=2))


def vector_field_ellipse(ax, cx, cy, rx, ry, color, seed=0, n=30):
    rng = np.random.default_rng(seed)
    th = rng.uniform(0, 2 * np.pi, n)
    rr = np.sqrt(rng.uniform(0.05, 1.0, n))
    xs = cx + rx * rr * np.cos(th)
    ys = cy + ry * rr * np.sin(th)
    us = rng.normal(0.5, 0.4, n)
    vs = rng.normal(0.3, 0.4, n)
    ax.quiver(xs, ys, us, vs, color=color, scale=45, width=0.007, zorder=3)


def vector_field(ax, x, y, w, h, color, seed=0, n=18):
    rng = np.random.default_rng(seed)
    xs = rng.uniform(x + 0.2, x + w - 0.2, n)
    ys = rng.uniform(y + 0.2, y + h - 0.2, n)
    us = rng.normal(0.6, 0.5, n)
    vs = rng.normal(0.4, 0.5, n)
    ax.quiver(xs, ys, us, vs, color=color, scale=55, width=0.008, zorder=3)


def wave_box(ax, x, y, w, h, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.2",
                                facecolor=color, edgecolor="none", zorder=2))
    xs = np.linspace(x + 0.15, x + w - 0.15, 40)
    ys = y + h / 2 + h * 0.22 * np.sin(np.linspace(0, 6 * np.pi, 40))
    ax.plot(xs, ys, color="white", lw=0.8, zorder=3)


def cnn_stack(ax, x, y, w, h=4.4, gap=1.5):
    items = [
        ("Conv 3×3", "#D6EEF5"), ("Norm & ReLU", "#E7F4E4"),
        ("MultiHead\nConv", "#FBE3C8"), ("Add & Norm", "#E7F4E4"),
        ("FeedForward\nConv", "#FBE3C8"), ("Add & Norm", "#E7F4E4"),
        ("MaxPooling", "#F7D9E0"), ("AvgPooling", "#D9E2F3"),
        ("MLP", "#D9EAD3"),
    ]
    yy = y
    centers = []
    for label, fill in items:
        ax.add_patch(FancyBboxPatch((x, yy), w, h, boxstyle="round,pad=0.08,rounding_size=0.5",
                                    facecolor=fill, edgecolor="#555555", lw=0.7, zorder=3))
        text(ax, x + w / 2, yy + h / 2, label, 6.4)
        centers.append(yy + h / 2)
        yy += h + gap
    # 竖向主箭头
    for i in range(len(centers) - 1):
        arrow(ax, (x + w / 2, centers[i] + h / 2), (x + w / 2, centers[i + 1] - h / 2),
              "#222222", 0.8)
    # 残差旁路（示意两条）
    for i in (2, 4):
        y1 = centers[i] - 0.4
        y2 = centers[i + 1] + 0.4
        xb = x - 2.2
        ax.plot([x, xb, xb, x], [y1, y1, y2, y2], color="#222222", lw=0.7, zorder=2)
        arrow(ax, (xb, y2), (x, y2), "#222222", 0.7)
    text(ax, x - 3.2, (centers[2] + centers[5]) / 2, "N×", 8)
    return centers


def render(out: Path) -> list[Path]:
    fig = plt.figure(figsize=(10.0, 8.95))   # 2000:1790，和原图同比
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 90)
    ax.axis("off")

    # ---------------- 容器 ----------------
    container(ax, 0.6, 64.0, 37.0, 25.0, C_A, "a", "Manifold with Boundary Representation for Images")
    container(ax, 0.6, 36.0, 18.0, 27.0, C_B, "b", "Vector Field")
    container(ax, 19.0, 36.0, 53.0, 27.0, C_C, "c", "Hodge Laplacian for Manifolds with Boundary")
    container(ax, 0.6, 0.8, 71.4, 34.0, C_D, "d", "Hodge Decomposition of Vector Fields")
    container(ax, 73.2, 0.8, 25.2, 62.0, C_E, "e", "CNN Architecture")
    container(ax, 73.2, 64.0, 25.2, 25.0, C_F, "f", "Classification")

    # ---------------- a: 流形表示 ----------------
    s = {(0, 0), (1, 0), (2, 0), (3, 0), (1, 1), (2, 1), (3, 1), (4, 1),
         (2, 2), (3, 2), (4, 2), (5, 2), (3, 3), (4, 3), (5, 3), (4, 4), (5, 4),
         (5, 5), (6, 5)}
    grid(ax, 2.0, 67.0, 9.0, 13.0, 8, 8, s, "#F2D7A0", nodes=True)
    text(ax, 6.5, 82.5, "Discrete Manifold", 6.0)
    ax.add_patch(Rectangle((12.5, 67.0), 9.0, 13.0, facecolor="white", edgecolor="#D8D8D8", lw=0.5, zorder=1))
    ax.add_patch(Polygon([[15.8, 70.5], [18.8, 73.0], [19.0, 76.5], [16.4, 79.2], [14.0, 77.2], [13.8, 73.2]],
                         closed=True, facecolor="#8FCFC9", edgecolor="none", zorder=2))
    text(ax, 17.0, 82.5, "Image", 6.0)
    s2 = {(1, 1), (2, 1), (2, 2), (3, 0), (3, 1), (3, 2), (3, 3), (4, 0), (4, 1),
          (4, 2), (5, 0), (5, 1), (5, 2), (6, 1), (6, 2)}
    grid(ax, 23.5, 67.0, 9.0, 13.0, 8, 8, s2, "#8CC63F", nodes=True, edge="#D8D8D8")
    text(ax, 28.0, 82.5, "Discrete Manifold", 6.0)
    arrow(ax, (11.2, 73.5), (12.3, 73.5), "#888888", 2.2)
    arrow(ax, (21.7, 73.5), (23.3, 73.5), "#888888", 2.2)
    text(ax, 11.7, 75.8, "Tangential\nBC", 4.6)
    text(ax, 22.2, 75.8, "Normal\nBC", 4.6)
    arrow(ax, (10.0, 64.2), (10.0, 63.2), C_A, 2.2)
    arrow(ax, (40.0, 64.2), (40.0, 63.2), C_A, 2.2)

    # ---------------- b: 向量场 ----------------
    grid(ax, 2.0, 40.0, 15.0, 18.0, 8, 8, None, "#F2D7A0")
    blob(ax, 9.5, 49.0, 6.2, "#F2D7A0", 11, 0.9)
    vector_field_ellipse(ax, 9.5, 49.0, 5.8, 6.8, "#7B3FA0", 3, 34)
    arrow(ax, (9.5, 36.5), (9.5, 34.8), C_B, 2.2)

    # ---------------- c: Hodge 谱 ----------------
    text(ax, 33.0, 58.3, "Harmonic Spectra", 5.6)
    text(ax, 58.0, 58.3, "Non-harmonic Spectra", 5.6)
    rng = np.random.default_rng(2)
    for i in range(20):
        y = 53.8 - i * 0.68
        color = ["#D9531E", "#3B82C4", "#6AA84F"][i % 3]
        ax.plot([21.5, 21.5 + rng.uniform(4, 14)], [y, y], color=color, lw=1.8, zorder=3)
    text(ax, 28.0, 56.9, "Ker$L_{k,n}$ ≅ $H_M^{m-k}(M)$", 5.2)
    text(ax, 28.0, 55.4, "Ker$L_{k,t}$ ≔ $H_{dR}^k(M)$", 5.2)
    ax.plot([44.5, 44.5], [38.5, 60.0], color="#DDDDDD", lw=0.8)
    for r, (rows, cols, color) in enumerate([(2, 2, "#6AA84F"), (2, 3, "#3B82C4"), (1, 5, "#D9531E")]):
        for i in range(rows):
            for j in range(cols):
                wave_box(ax, 46.0 + j * 4.3, 53.0 - i * 4.5 - r * 5.2, 3.8, 3.8, color)
    arrow(ax, (46.0, 36.5), (46.0, 34.8), C_C, 2.2)

    # ---------------- d: Hodge 分解 ----------------
    cols = [
        ("Curl-free", "#D9531E", "#F4C7A8", 4.0),
        ("Divergence-free", "#3B82C4", "#F4C7A8", 21.0),
        ("Harmonic", "#6AA84F", "#F4C7A8", 38.0),
        ("Vector Field", "#7B3FA0", "#F4C7A8", 55.0),
    ]
    for name, color, fill, x in cols:
        text(ax, x + 7.0, 31.0, name, 6.0)
        grid(ax, x, 18.0, 14.0, 11.0, 6, 5, None, fill)
        blob(ax, x + 7.0, 23.5, 5.0, fill, int(x) + 1, 0.9)
        vector_field_ellipse(ax, x + 7.0, 23.5, 4.6, 4.4, color, int(x), 26)
        arrow(ax, (x + 7.0, 16.8), (x + 7.0, 15.2), "#999999", 1.6)
        blob(ax, x + 7.0, 7.5, 4.6, color, int(x), 0.95)
    text(ax, 19.0, 23.8, "+", 15, color="#999999")
    text(ax, 36.0, 23.8, "+", 15, color="#999999")
    text(ax, 53.0, 23.8, "=", 15, color="#999999")
    text(ax, 54.0, 7.5, "→", 12, color="#999999")
    # 重叠的三色块
    blob(ax, 62.0, 7.0, 5.0, "#D9531E", 1, 0.8)
    blob(ax, 64.0, 8.5, 5.0, "#3B82C4", 2, 0.7)
    blob(ax, 66.0, 7.5, 5.0, "#6AA84F", 3, 0.8)
    arrow(ax, (70.2, 19.0), (73.0, 19.0), C_D, 2.8)

    # ---------------- e: CNN ----------------
    cnn_stack(ax, 79.5, 7.5, 12.5)
    arrow(ax, (85.8, 62.6), (85.8, 66.0), C_E, 2.6)

    # ---------------- f: 分类 ----------------
    star = [[82.0, 72.5], [84.0, 77.5], [88.0, 79.0], [86.5, 83.0], [90.0, 84.0],
            [88.0, 87.5], [84.0, 86.0], [82.0, 82.5], [79.0, 84.0], [78.5, 80.0],
            [76.5, 77.0], [79.5, 75.5]]
    cx, cy = 84.5, 80.0
    star = [[cx + 0.72 * (x - cx), cy + 0.72 * (y - cy)] for x, y in star]
    ax.add_patch(Polygon(star, closed=True, facecolor="#E86A6A", edgecolor="none", zorder=2))
    text(ax, 83.5, 80.5, "malignant", 5.8)
    ax.add_patch(Polygon([[79.0, 73.5], [81.0, 76.5], [79.0, 79.5], [77.0, 76.5]],
                         closed=True, facecolor="#F4B942", edgecolor="none", zorder=2))
    text(ax, 77.6, 76.5, "normal", 5.8)
    ax.add_patch(Polygon([[91.5, 75.0], [95.0, 76.5], [96.0, 79.5], [93.0, 81.0], [90.0, 79.0]],
                         closed=True, facecolor="#4A90D9", edgecolor="none", zorder=2))
    text(ax, 93.0, 78.2, "benign", 5.8)
    ax.add_patch(FancyBboxPatch((78.0, 66.8), 10.0, 2.6, boxstyle="round,pad=0.1,rounding_size=0.5",
                                facecolor="#EAF4F8", edgecolor="#555555", lw=0.7, zorder=3))
    text(ax, 83.0, 68.1, "Softmax", 6.0)
    arrow(ax, (83.0, 69.5), (83.0, 72.0), "#222222", 0.8)

    out.parent.mkdir(parents=True, exist_ok=True)
    files = []
    for ext in ("png", "pdf"):
        p = out.with_suffix(f".{ext}")
        fig.savefig(p, dpi=300)   # 不裁边：保证 0-100/0-90 画布和原图一一对应
        files.append(p)
    plt.close(fig)
    return files


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="figures/repro/MTDL_arch")
    args = ap.parse_args()
    print(render(Path(args.out)))


if __name__ == "__main__":
    main()
