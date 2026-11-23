"""复刻矩阵小倍数图：行=模型，列=条件，共享色标/坐标，行列标签只出现一次。

用法：
  py tools/repro_matrix.py --demo --out figures/repro
  py tools/repro_matrix.py --spec figures/repro/matrix.json --out figures/repro

数据是合成的（用于验证版式），不是原论文数据；图注会标明"结构复刻，数据为示意"。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def field(seed: int, h: int = 300, w: int = 100) -> np.ndarray:
    """合成一张有丝状结构的涡度场（仅用于版式复刻）。"""
    rng = np.random.default_rng(seed)
    f = rng.normal(size=(h, w))
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    low = np.exp(-((fx / 0.035) ** 2 + (fy / 0.10) ** 2))
    high = np.exp(-((fx / 0.14) ** 2 + (fy / 0.05) ** 2))
    fa = np.fft.fft2(f)
    s = 0.65 * np.real(np.fft.ifft2(fa * low)) + 0.35 * np.real(np.fft.ifft2(fa * high))
    # 沿 x 做轻微剪切，制造丝状结构
    for row in range(h):
        s[row] = np.roll(s[row], int(6 * np.sin(row / 18.0)))
    yy, xx = np.mgrid[0:h, 0:w]
    for _ in range(3):
        cx, cy = rng.uniform(0.2, 0.8) * w, rng.uniform(0.2, 0.8) * h
        r2 = (xx - cx) ** 2 + (yy - cy) ** 2
        s += rng.choice([-1, 1]) * 2.2 * np.exp(-r2 / (2 * (w * 0.05) ** 2))
    s = (s - s.mean()) / (s.std() + 1e-9)
    return np.clip(s * 0.9, -3, 3)


def render(spec: dict, out: Path) -> list[Path]:
    rows = spec.get("rows", ["MPAS-O", "ROMS"])
    cols = spec.get("cols", [f"Δx = {x}" for x in
                             ["10 km", "5 km", "2 km", "1 km", "500 m", "200 m", "100 m"]])
    R, C = len(rows), len(cols)
    vmin, vmax = spec.get("vmin", -3), spec.get("vmax", 3)
    cmap = spec.get("cmap", "RdBu_r")
    W, H = spec.get("size", [7.4, 5.1])

    fig = plt.figure(figsize=(W, H))
    gs = fig.add_gridspec(R, C, left=0.075, right=0.90, top=0.90, bottom=0.10,
                          wspace=0.06, hspace=0.12)
    axes = [[fig.add_subplot(gs[r, c]) for c in range(C)] for r in range(R)]

    for r in range(R):
        for c in range(C):
            ax = axes[r][c]
            im = ax.imshow(field(r * 100 + c), cmap=cmap, vmin=vmin, vmax=vmax,
                           aspect="auto", interpolation="bilinear", origin="lower")
            ax.set_xticks([])
            ax.set_yticks([])
            for s in ax.spines.values():
                s.set_linewidth(0.6)
            if r == 0:
                ax.set_title(cols[c], fontsize=7.5, pad=3)
            if c == 0:
                ax.set_yticks([0, 75, 150, 225, 299])
                ax.set_yticklabels(["0", "100", "200", "300", ""], fontsize=6.5)
            if r == R - 1:
                ax.set_xticks([0, 24, 49, 74, 99])
                ax.set_xticklabels(["0", "25", "50", "75", "100"], fontsize=6.5)
                ax.set_xlabel("X [km]", fontsize=7, labelpad=1)
            ax.text(0.03, 0.95, f"({chr(97 + r * C + c)})", transform=ax.transAxes,
                    ha="left", va="top", fontsize=6.5, color="#222",
                    bbox=dict(boxstyle="square,pad=0.12", fc="white", ec="#999", lw=0.5))

        fig.text(0.028, 1 - (r + 0.5) / R * 0.90 - 0.05, rows[r], rotation=90,
                 va="center", ha="center", fontsize=12)
        cb = fig.colorbar(im, ax=axes[r], orientation="vertical", fraction=0.018,
                          pad=0.008, aspect=28)
        cb.set_label("ζ/f", fontsize=8, rotation=90, labelpad=2)
        cb.ax.tick_params(labelsize=6.5, length=2)
        cb.outline.set_linewidth(0.5)

    out.parent.mkdir(parents=True, exist_ok=True)
    files = []
    for ext in ("png", "pdf"):
        p = out.with_suffix(f".{ext}")
        fig.savefig(p, dpi=300, bbox_inches="tight", pad_inches=0.02)
        files.append(p)
    plt.close(fig)
    return files


def demo(out: Path) -> None:
    spec = {
        "rows": ["MPAS-O", "ROMS"],
        "cols": ["Δx = 10 km", "Δx = 5 km", "Δx = 2 km", "Δx = 1 km",
                 "Δx = 500 m", "Δx = 200 m", "Δx = 100 m"],
        "vmin": -3, "vmax": 3, "cmap": "RdBu_r", "size": [7.4, 4.6],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    (out.parent / "matrix.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2),
                                            encoding="utf-8")
    print(render(spec, out))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--spec", default="")
    ap.add_argument("--out", default="figures/repro/GMD_matrix")
    args = ap.parse_args()
    out = Path(args.out)
    if args.demo:
        demo(out)
    else:
        print(render(json.loads(Path(args.spec).read_text(encoding="utf-8")), out))


if __name__ == "__main__":
    main()
