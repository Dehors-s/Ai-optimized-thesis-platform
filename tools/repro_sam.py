"""复刻 SAM overview（arXiv:2304.02643 Fig. 4）：图像→编码器→嵌入→提示→掩码解码→三掩码。

用法：
  py tools/repro_sam.py --out figures/repro/SAM_overview

说明：输入图与掩码是合成的示例素材（不复制原图照片），只复刻版式与流程；
图注需注明"结构复刻，图像为示例"。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["DejaVu Serif"]
plt.rcParams["axes.unicode_minus"] = False

GREEN = ("#E8F7E8", "#4CAF50")
ORANGE = ("#FFE8CC", "#F4A261")
PURPLE = ("#E8DAF5", "#9B59B6")
YELLOW = ("#FFF3CC", "#9B59B6")
GREY = "#CFCFCF"


def make_assets(dir_: Path) -> None:
    dir_.mkdir(parents=True, exist_ok=True)
    W, H = 320, 220
    rng = np.random.default_rng(7)
    # 木纹背景
    yy, xx = np.mgrid[0:H, 0:W]
    base = np.zeros((H, W, 3), dtype=np.uint8)
    base[..., 0] = np.clip(120 + 30 * np.sin(yy / 9) + rng.normal(0, 8, (H, W)), 0, 255)
    base[..., 1] = np.clip(75 + 18 * np.sin(yy / 11) + rng.normal(0, 6, (H, W)), 0, 255)
    base[..., 2] = np.clip(40 + 10 * np.sin(yy / 13) + rng.normal(0, 5, (H, W)), 0, 255)
    img = Image.fromarray(base.astype(np.uint8), "RGB")
    d = ImageDraw.Draw(img)

    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    # 剪刀状物体：两条交叉粗线 + 两个环
    d.line([(70, 60), (190, 175)], fill=(40, 40, 45), width=18)
    d.line([(70, 175), (190, 60)], fill=(35, 35, 40), width=18)
    d.ellipse([55, 40, 105, 90], outline=(30, 30, 35), width=10)
    d.ellipse([155, 130, 205, 180], outline=(30, 30, 35), width=10)
    md.line([(70, 60), (190, 175)], fill=255, width=22)
    md.line([(70, 175), (190, 60)], fill=255, width=22)
    md.ellipse([55, 40, 105, 90], outline=255, width=14)
    md.ellipse([155, 130, 205, 180], outline=255, width=14)
    # 红色小物件
    d.rectangle([240, 20, 300, 70], fill=(190, 40, 40))
    md.rectangle([235, 15, 305, 75], fill=180)
    img.save(dir_ / "sam_input.png")

    arr = np.array(img).astype(np.float32)
    m = np.array(mask) > 0
    for i, color in enumerate([(60, 130, 230), (40, 170, 90), (230, 140, 40)], 1):
        out = arr.copy()
        out[m] = 0.35 * out[m] + 0.65 * np.array(color, dtype=np.float32)
        Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dir_ / f"sam_mask{i}.png")


def _box(ax, x, y, w, h, text, colors, fs=7.5):
    fill, edge = colors
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6,rounding_size=2.5",
                                facecolor=fill, edgecolor=edge, linewidth=1.0, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, zorder=3)


def _arrow(ax, p1, p2, style="-|>"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=6,
                                 color="#222222", lw=0.8, zorder=1, shrinkA=0, shrinkB=0))


def render(out: Path, assets: Path) -> list[Path]:
    fig = plt.figure(figsize=(8.7, 1.6))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 870)
    ax.set_ylim(0, 160)
    ax.axis("off")

    # 输入图
    ax.imshow(plt.imread(assets / "sam_input.png"), extent=[2, 140, 58, 150], zorder=0)
    ax.text(58, 44, "image", ha="center", va="center", fontsize=7.5)
    _arrow(ax, (142, 104), (168, 104))

    # 图像编码器
    _box(ax, 170, 52, 235, 75, "image\nencoder", GREEN, 8)
    _arrow(ax, (407, 88), (425, 88))

    # 图像嵌入（四个小方块）
    for i in range(4):
        ax.add_patch(plt.Rectangle((430, 96 - i * 13), 14, 11, facecolor=GREY,
                                   edgecolor="#8A8A8A", lw=0.6, zorder=2))
    ax.text(424, 28, "image\nembedding", ha="center", va="center", fontsize=6.4)
    _arrow(ax, (446, 108), (470, 108))

    # 加号
    ax.add_patch(Circle((480, 108), 8, facecolor="white", edgecolor="#222222", lw=0.9, zorder=2))
    ax.plot([476, 484], [108, 108], color="#222222", lw=0.8, zorder=3)
    ax.plot([480, 480], [104, 112], color="#222222", lw=0.8, zorder=3)

    # 掩码卷积（梯形）
    ax.add_patch(Polygon([(466, 74), (494, 74), (500, 94), (460, 94)],
                         closed=True, facecolor=YELLOW[0], edgecolor=YELLOW[1], lw=0.9, zorder=2))
    ax.text(480, 84, "conv", ha="center", va="center", fontsize=7)
    ax.text(496, 24, "mask", ha="center", va="center", fontsize=6.8)
    _arrow(ax, (480, 34), (480, 72))
    _arrow(ax, (480, 96), (480, 99))

    # 掩码解码器
    _box(ax, 530, 92, 120, 30, "mask decoder", ORANGE, 8)
    _arrow(ax, (489, 108), (526, 108))

    # 提示编码器
    _box(ax, 540, 58, 170, 28, "prompt encoder", PURPLE, 8)
    _arrow(ax, (625, 87), (625, 91))
    for x, label in [(560, "points"), (630, "box"), (700, "text")]:
        ax.text(x, 30, label, ha="center", va="center", fontsize=7.5)
        _arrow(ax, (x, 38), (x, 56))

    # 输出掩码
    for i, y0 in enumerate([124, 96, 68], 1):
        ax.imshow(plt.imread(assets / f"sam_mask{i}.png"), extent=[735, 805, y0, y0 + 22], zorder=0)
        ax.text(807, y0 + 11, ", score", ha="left", va="center", fontsize=6.2)
        # 从解码器右侧折到掩码
        ax.plot([650, 726, 726], [107, 107, y0 + 13], color="#222222", lw=0.8, zorder=1)
        _arrow(ax, (726, y0 + 13), (733, y0 + 13))
    ax.text(770, 46, "valid masks", ha="center", va="center", fontsize=6.4)

    out.parent.mkdir(parents=True, exist_ok=True)
    files = []
    for ext in ("png", "pdf", "svg"):
        p = out.with_suffix(f".{ext}")
        fig.savefig(p, dpi=400, bbox_inches="tight", pad_inches=0.01)
        files.append(p)
    plt.close(fig)
    return files


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="figures/repro/SAM_overview")
    ap.add_argument("--assets", default="figures/repro/assets")
    args = ap.parse_args()
    assets = Path(args.assets)
    make_assets(assets)
    print(render(Path(args.out), assets))


if __name__ == "__main__":
    main()
