"""部件库 + 拼装器：复合图 = 语义部件 × 拼装。

用法：
  py tools/panelkit.py list
  py tools/panelkit.py demo --out figures/repro/panels_contact.png
  py tools/panelkit.py compose --layout figures/repro/layout.json --out figures/repro/composite

部件约定：render(ax, spec=None)，只在 0—1 坐标内画，不关心全局位置。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import (Circle, FancyArrowPatch, FancyBboxPatch,  # noqa: E402
                                Polygon, Rectangle)

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parents[1]
REG = {}
_WORLD = None

# 部件元数据：数据范围、是否自带色标。容器可用 panel_meta / spec.data_range 覆盖。
META = {
    "map": {"data_range": (-3.0, 3.0), "has_colorbar": False},
    "heatmap": {"data_range": (0.0, 1.0), "has_colorbar": True},
    "contour": {"data_range": (0.0, 1.5), "has_colorbar": True},
    "quiver": {"data_range": None, "has_colorbar": False},
    "cnn-stack": {"data_range": None, "has_colorbar": False},
    "classification": {"data_range": None, "has_colorbar": False},
    "pipeline": {"data_range": None, "has_colorbar": False},
    "spectra": {"data_range": None, "has_colorbar": False},
    "vector-field": {"data_range": None, "has_colorbar": False},
    "manifold": {"data_range": None, "has_colorbar": False},
    "decomp": {"data_range": None, "has_colorbar": False},
    "qualitative": {"data_range": None, "has_colorbar": False},
}


def panel_meta(container: dict) -> dict:
    base = dict(META.get(container.get("panel"), {"data_range": None, "has_colorbar": False}))
    base.update(container.get("panel_meta") or {})
    spec = container.get("spec") or {}
    if spec.get("data_range") is not None:
        base["data_range"] = tuple(spec["data_range"])
    return base


def panel(name):
    def deco(fn):
        REG[name] = fn
        return fn
    return deco


def _arrow(ax, p1, p2, color="#333333", lw=1.0, ms=7):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=ms,
                                 color=color, lw=lw, zorder=3, shrinkA=0, shrinkB=0))


def _box(ax, x, y, w, h, text, fill="#F2F2F2", edge="#777777", fs=7):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.02",
                                facecolor=fill, edgecolor=edge, lw=0.8, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, zorder=3)


def _blob(ax, cx, cy, r, color, seed=0, noise=0.10, alpha=0.95):
    rng = np.random.default_rng(seed)
    th = np.linspace(0, 2 * np.pi, 30, endpoint=False)
    rr = r * (1 + noise * rng.normal(size=30))
    ax.add_patch(Polygon(np.c_[cx + rr * np.cos(th), cy + rr * np.sin(th)], closed=True,
                         facecolor=color, edgecolor="none", alpha=alpha, zorder=2))


@panel("cnn-stack")
def cnn_stack(ax, spec=None):
    items = [("MLP", "#D9EAD3"), ("AvgPool", "#D9E2F3"), ("MaxPool", "#F7D9E0"),
             ("Add & Norm", "#E7F4E4"), ("FFN", "#FBE3C8"), ("Add & Norm", "#E7F4E4"),
             ("MultiHead", "#FBE3C8"), ("Norm", "#E7F4E4"), ("Conv3×3", "#D6EEF5")]
    n = len(items)
    h = 0.075
    gap = (0.88 - n * h) / (n - 1)
    y = 0.06
    cs = []
    for label, fill in items:
        _box(ax, 0.28, y, 0.44, h, label, fill, fs=6.5)
        cs.append(y + h / 2)
        y += h + gap
    for i in range(n - 1):
        _arrow(ax, (0.50, cs[i] + h / 2), (0.50, cs[i + 1] - h / 2), "#222", 0.7, 6)
    for i in (3, 5):
        xb = 0.24
        ax.plot([0.28, xb, xb, 0.28], [cs[i], cs[i], cs[i + 1], cs[i + 1]],
                color="#222", lw=0.6, zorder=1)
    ax.text(0.16, (cs[3] + cs[5]) / 2, "N×", fontsize=7)


@panel("classification")
def classification(ax, spec=None):
    star = [[0.55, 0.55], [0.58, 0.70], [0.68, 0.72], [0.65, 0.82], [0.72, 0.88],
            [0.62, 0.90], [0.56, 0.98], [0.50, 0.90], [0.40, 0.92], [0.39, 0.82],
            [0.32, 0.76], [0.40, 0.70], [0.42, 0.60]]
    ax.add_patch(Polygon(star, closed=True, facecolor="#E86A6A", edgecolor="none", zorder=2))
    ax.text(0.53, 0.75, "malignant", fontsize=6, ha="center")
    ax.add_patch(Polygon([[0.18, 0.45], [0.24, 0.52], [0.18, 0.59], [0.12, 0.52]],
                         closed=True, facecolor="#F4B942", edgecolor="none", zorder=2))
    ax.text(0.12, 0.52, "normal", fontsize=6, ha="center")
    ax.add_patch(Polygon([[0.82, 0.45], [0.92, 0.48], [0.94, 0.55], [0.86, 0.60], [0.78, 0.55]],
                         closed=True, facecolor="#4A90D9", edgecolor="none", zorder=2))
    ax.text(0.86, 0.52, "benign", fontsize=6, ha="center")
    _box(ax, 0.36, 0.18, 0.28, 0.10, "Softmax", "#EAF4F8", "#555", 6.5)
    _arrow(ax, (0.50, 0.28), (0.50, 0.42), "#222", 0.8, 6)


@panel("spectra")
def spectra(ax, spec=None):
    rng = np.random.default_rng(3)
    for i in range(14):
        y = 0.86 - i * 0.05
        c = ["#D9531E", "#3B82C4", "#6AA84F"][i % 3]
        ax.plot([0.05, 0.05 + rng.uniform(0.12, 0.38)], [y, y], color=c, lw=1.4, zorder=2)
    ax.text(0.22, 0.93, "Harmonic Spectra", fontsize=6, ha="center")
    ax.text(0.22, 0.86, "Ker$L_{k,n}$ ≅ $H_M^{m-k}$", fontsize=5.5, ha="center")
    for r, (rows, cols, color) in enumerate([(2, 2, "#6AA84F"), (2, 3, "#3B82C4"), (1, 5, "#D9531E")]):
        for i in range(rows):
            for j in range(cols):
                x = 0.55 + j * 0.075
                y = 0.78 - i * 0.09 - r * 0.10
                ax.add_patch(FancyBboxPatch((x, y), 0.065, 0.065,
                                            boxstyle="round,pad=0.003,rounding_size=0.01",
                                            facecolor=color, edgecolor="none", zorder=2))
                xs = np.linspace(x + 0.008, x + 0.057, 30)
                ax.plot(xs, y + 0.032 + 0.018 * np.sin(np.linspace(0, 6 * np.pi, 30)),
                        color="white", lw=0.6, zorder=3)
    ax.text(0.67, 0.93, "Non-harmonic", fontsize=6, ha="center")


@panel("vector-field")
def vector_field(ax, spec=None):
    for i in range(1, 8):
        ax.plot([i / 8] * 2, [0, 1], color="#E4E4E4", lw=0.5, zorder=0)
        ax.plot([0, 1], [i / 8] * 2, color="#E4E4E4", lw=0.5, zorder=0)
    _blob(ax, 0.50, 0.50, 0.30, "#F2D7A0", 5)
    rng = np.random.default_rng(3)
    n = 26
    th = rng.uniform(0, 2 * np.pi, n)
    rr = np.sqrt(rng.uniform(0.02, 1.0, n))
    xs = 0.50 + 0.27 * rr * np.cos(th)
    ys = 0.50 + 0.27 * rr * np.sin(th)
    ax.quiver(xs, ys, rng.normal(0.5, 0.4, n), rng.normal(0.3, 0.4, n),
              color="#7B3FA0", scale=18, width=0.006, zorder=3)


def _world() -> list:
    global _WORLD
    if _WORLD is not None:
        return _WORLD
    import shapefile
    shp = ROOT / "corpus" / "geo" / "countries" / "ne_110m_admin_0_countries.shp"
    rings = []
    for sh in shapefile.Reader(str(shp)).shapes():
        pts, parts = sh.points, list(sh.parts) + [len(sh.points)]
        for i in range(len(parts) - 1):
            ring = pts[parts[i]:parts[i + 1]]
            if len(ring) >= 3:
                rings.append(ring)
    _WORLD = rings
    return rings


@panel("map")
def map_panel(ax, spec=None):
    """经纬度底图 + 散点；spec.data_range 决定着色范围。"""
    def xy(lon, lat):
        return (lon + 180) / 360, (lat + 60) / 150

    lo, hi = (spec or {}).get("data_range", (-3.0, 3.0))

    for ring in _world():
        pts = [xy(lon, lat) for lon, lat in ring]
        ax.add_patch(Polygon(pts, closed=True, facecolor="#F4F4F4", edgecolor="#C8C8C8",
                             lw=0.4, zorder=1))
    for lon in range(-180, 181, 60):
        x, _ = xy(lon, 0)
        ax.plot([x, x], [0, 1], color="#E4E4E4", lw=0.4, ls=":", zorder=0)
    for lat in range(-60, 91, 30):
        _, y = xy(0, lat)
        ax.plot([0, 1], [y, y], color="#E4E4E4", lw=0.4, ls=":", zorder=0)
    rng = np.random.default_rng(12)
    n = 90
    lons = rng.uniform(-170, 170, n)
    lats = rng.uniform(-50, 75, n)
    vals = rng.uniform(lo, hi, n)
    xs, ys = xy(lons, lats)
    ax.scatter(xs, ys, c=vals, cmap="YlGnBu", vmin=lo, vmax=hi, s=5,
               edgecolors="none", zorder=3)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)


@panel("heatmap")
def _heatmap_panel(ax, spec=None):
    from paneltemplates import heatmap as _hm
    _hm(ax)


@panel("contour")
def _contour_panel(ax, spec=None):
    from paneltemplates import contour as _ct
    _ct(ax)


@panel("manifold")
def manifold(ax, spec=None):
    """三个子面板：离散流形 → 图像 → 离散流形，带边界条件箭头。"""
    def grid(x0, y0, w, h, cells, fill, nodes=False):
        for i in range(9):
            ax.plot([x0 + w * i / 8] * 2, [y0, y0 + h], color="#E4E4E4", lw=0.45, zorder=0)
            ax.plot([x0, x0 + w], [y0 + h * i / 8] * 2, color="#E4E4E4", lw=0.45, zorder=0)
        for (i, j) in cells:
            ax.add_patch(Rectangle((x0 + w * i / 8, y0 + h * j / 8), w / 8, h / 8,
                                   facecolor=fill, edgecolor="none", zorder=1))
        if nodes:
            for (i, j) in cells:
                for (a, b) in ((i, j), (i + 1, j), (i, j + 1), (i + 1, j + 1)):
                    ax.plot(x0 + w * a / 8, y0 + h * b / 8, "o", ms=1.5,
                            color="#2E6DA4", zorder=2)

    grid(0.02, 0.16, 0.28, 0.66,
         {(0, 0), (1, 0), (2, 0), (1, 1), (2, 1), (3, 1), (2, 2), (3, 2), (4, 2), (3, 3), (4, 3)},
         "#F2D7A0", True)
    grid(0.35, 0.16, 0.30, 0.66, set(), "#F2D7A0")
    ax.add_patch(Polygon([[0.42, 0.32], [0.56, 0.42], [0.58, 0.58], [0.50, 0.72], [0.40, 0.62],
                          [0.37, 0.45]], closed=True, facecolor="#8FCFC9", edgecolor="none", zorder=2))
    grid(0.68, 0.16, 0.28, 0.66,
         {(1, 1), (2, 1), (2, 2), (3, 0), (3, 1), (3, 2), (3, 3), (4, 0), (4, 1), (4, 2), (5, 0), (5, 1)},
         "#8CC63F", True)
    ax.text(0.16, 0.90, "Discrete Manifold", fontsize=5.2, ha="center")
    ax.text(0.50, 0.90, "Image", fontsize=5.2, ha="center")
    ax.text(0.82, 0.90, "Discrete Manifold", fontsize=5.2, ha="center")
    _arrow(ax, (0.30, 0.50), (0.35, 0.50), "#777", 1.2, 7)
    _arrow(ax, (0.65, 0.50), (0.68, 0.50), "#777", 1.2, 7)
    ax.text(0.325, 0.57, "Tangential BC", fontsize=4.0, ha="center")
    ax.text(0.665, 0.57, "Normal BC", fontsize=4.0, ha="center")


@panel("decomp")
def decomp(ax, spec=None):
    cols = [("curl-free", "#D9531E"), ("div-free", "#3B82C4"),
            ("harmonic", "#6AA84F"), ("field", "#7B3FA0")]
    for k, (name, color) in enumerate(cols):
        x = 0.02 + k * 0.25
        ax.add_patch(Rectangle((x, 0.55), 0.20, 0.30, facecolor="white",
                               edgecolor="#DDDDDD", lw=0.6, zorder=1))
        _blob(ax, x + 0.10, 0.70, 0.08, "#F2D7A0", k + 2, 0.10)
        rng = np.random.default_rng(k)
        n = 10
        ax.quiver(x + 0.10 + rng.normal(0, 0.03, n), 0.70 + rng.normal(0, 0.03, n),
                  rng.normal(0.2, 0.2, n), rng.normal(0.2, 0.2, n),
                  color=color, scale=6, width=0.008, zorder=3)
        ax.text(x + 0.10, 0.87, name, fontsize=5.2, ha="center")
        _blob(ax, x + 0.10, 0.25, 0.09, color, k + 5, 0.12)
        _arrow(ax, (x + 0.10, 0.53), (x + 0.10, 0.37), "#999", 0.8, 5)
        if k < 3:
            ax.text(x + 0.225, 0.68, "+" if k < 2 else "=", fontsize=10,
                    color="#999", ha="center", va="center")


def render_panel(name: str, out: Path, size=(3.2, 3.2)) -> Path:
    fig, ax = plt.subplots(figsize=size)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    REG[name](ax)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return out


def demo(out: Path) -> None:
    names = list(REG)
    cols = 3
    rows = (len(names) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(9.6, 3.2 * rows))
    for ax, name in zip(axes.ravel(), names):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        REG[name](ax)
        ax.set_title(name, fontsize=9, loc="left")
    for ax in axes.ravel()[len(names):]:
        ax.axis("off")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=220, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def layout_lint(layout: dict) -> list[dict]:
    """拼装层检查：几何、字母、面板注册、标题溢出、面板过小。"""
    issues = []

    def add(level, rule, msg):
        issues.append({"level": level, "rule": rule, "msg": msg})

    cs = layout.get("containers", [])
    if len(cs) < 2:
        add("warn", "C0", "容器少于 2 个，可能不是复合图")
    rects = []
    letters = []
    titles = []
    for idx, c in enumerate(cs, 1):
        x, y, w, h = c["rect"]
        name = f"{c.get('letter', '?')}#{idx}"
        rects.append((name, x, y, w, h))
        letters.append(c.get("letter", ""))
        titles.append(c.get("title", ""))
        if x < -1e-6 or y < -1e-6 or x + w > 1 + 1e-6 or y + h > 1 + 1e-6:
            add("fail", "C1", f"{name} 越界：{c['rect']}")
        if c.get("panel") not in REG:
            add("fail", "C5", f"{name} 引用了未注册面板 {c.get('panel')}")
        if w - 0.016 < 0.04 or h - 0.05 < 0.04:
            add("warn", "C7", f"{name} 面板过小：内框 {w-0.016:.3f}×{h-0.05:.3f}")
        if not c.get("letter"):
            add("warn", "C4", f"{name} 缺少字母")
        est = len(c.get("title", "")) * 0.0045 + 0.020
        if est > w - 0.004:
            add("warn", "C6", f"{name} 标题可能溢出（估算 {est:.2f} > {w-0.004:.2f}）")

    if len(set(letters)) != len(letters):
        add("fail", "C4", f"字母重复：{letters}")
    nonempty = [t for t in titles if t]
    if len(set(nonempty)) != len(nonempty):
        add("warn", "C8", "标题有重复")

    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            n1, x1, y1, w1, h1 = rects[i]
            n2, x2, y2, w2, h2 = rects[j]
            ix = max(0.0, min(x1 + w1, x2 + w2) - max(x1, x2))
            iy = max(0.0, min(y1 + h1, y2 + h2) - max(y1, y2))
            if ix > 1e-6 and iy > 1e-6:
                add("fail", "C2", f"{n1} 与 {n2} 重叠 {ix:.3f}×{iy:.3f}")
                continue
            dx = max(x2 - (x1 + w1), x1 - (x2 + w2), 0.0)
            dy = max(y2 - (y1 + h1), y1 - (y2 + h2), 0.0)
            if 0 < dx < 0.003:
                add("warn", "C3", f"{n1} 与 {n2} 水平间距 {dx:.3f} 过小")
            if 0 < dy < 0.003:
                add("warn", "C3", f"{n1} 与 {n2} 垂直间距 {dy:.3f} 过小")

    # ---------------- 共享元素 ----------------
    shared = layout.get("shared") or {}
    by_letter = {c.get("letter"): c["rect"] for c in cs if c.get("letter")}
    by_container = {c.get("letter"): c for c in cs if c.get("letter")}

    cbs = shared.get("colorbars") or []
    ids, owners, signatures = [], {}, {}
    for i, cb in enumerate(cbs):
        drs = []
        cid = cb.get("id") or f"cb{i+1}"
        ids.append(cid)
        rng = cb.get("range")
        if not (isinstance(rng, (list, tuple)) and len(rng) == 2 and rng[0] < rng[1]):
            add("fail", "C9", f"{cid} 的 range 非法：{rng}")
        if cb.get("placement", "right") not in ("right", "left", "bottom", "top"):
            add("warn", "C9", f"{cid} 的 placement 未知：{cb.get('placement')}")
        if isinstance(rng, (list, tuple)) and len(rng) == 2:
            for t in cb.get("ticks", []) or []:
                if not (rng[0] <= t <= rng[1]):
                    add("warn", "C13", f"{cid} 的刻度 {t} 不在 range 内")
        for p in cb.get("panels", []):
            if p not in by_letter:
                add("warn", "C9", f"{cid} 引用了不存在的面板 {p}")
            if p in owners:
                add("warn", "C9", f"{p} 同时属于色标 {owners[p]} 和 {cid}")
            owners[p] = cid
            c = by_container.get(p)
            if c and isinstance(rng, (list, tuple)) and len(rng) == 2:
                meta = panel_meta(c)
                if meta.get("has_colorbar"):
                    add("warn", "C13", f"{p}({c.get('panel')}) 自带色标，与共享色标 {cid} 重复")
                dr = meta.get("data_range")
                if dr is None:
                    add("warn", "C13", f"{p}({c.get('panel')}) 无 data_range，无法核验色标范围")
                elif dr[0] < rng[0] - 1e-6 or dr[1] > rng[1] + 1e-6:
                    add("fail", "C13",
                        f"{cid} 范围 [{rng[0]},{rng[1]}] 未覆盖 {p} 数据 [{dr[0]},{dr[1]}]")
                if dr is not None:
                    drs.append(dr)
        if drs and isinstance(rng, (list, tuple)) and len(rng) == 2 and rng[1] > rng[0]:
            lo = min(d[0] for d in drs)
            hi = max(d[1] for d in drs)
            ratio = (hi - lo) / (rng[1] - rng[0])
            if ratio < 0.6:
                add("warn", "C14",
                    f"{cid} 数据只占色标 {ratio:.0%}，范围 [{rng[0]},{rng[1]}] 过宽")
        sig = (cb.get("label", ""), tuple(rng) if isinstance(rng, (list, tuple)) else ())
        if sig in signatures:
            add("warn", "C9", f"{cid} 与 {signatures[sig]} 的色标重复（label+range 相同）")
        else:
            signatures[sig] = cid
    if len(set(ids)) != len(ids):
        add("fail", "C9", f"色标 id 重复：{ids}")

    def _group_check(kind, items, rule):
        seen = {}
        for i, it in enumerate(items):
            ps = it.get("panels", [])
            if not ps:
                add("warn", rule, f"{kind}#{i+1} 没有 panels")
                continue
            missing = [p for p in ps if p not in by_letter]
            if missing:
                add("fail", rule, f"{kind}#{i+1} 引用了不存在的面板 {missing}")
            rs = [by_letter[p] for p in ps if p in by_letter]
            if not rs:
                continue
            for p in ps:
                if p in seen:
                    add("fail", rule, f"{p} 同时属于两个{kind}")
                seen[p] = it.get("text", "")
            text = it.get("text", "")
            if kind == "行标签":
                ys = [r[1] for r in rs]
                hs = [r[3] for r in rs]
                ws = [r[2] for r in rs]
                if max(ys) - min(ys) > 0.006:
                    add("warn", rule, f"{text} 的底缘不齐")
                if max(hs) - min(hs) > 0.01:
                    add("warn", rule, f"{text} 的高度不一致")
                if max(ws) - min(ws) > 0.01:
                    add("warn", rule, f"{text} 的宽度不一致")
                xs = sorted(r[0] for r in rs)
                gaps = [xs[k + 1] - xs[k] for k in range(len(xs) - 1)]
                if gaps and max(gaps) - min(gaps) > 0.01:
                    add("warn", rule, f"{text} 的面板间距不一致")
            else:
                xs = [r[0] for r in rs]
                ws = [r[2] for r in rs]
                hs = [r[3] for r in rs]
                if max(xs) - min(xs) > 0.006:
                    add("warn", rule, f"{text} 的左缘不齐")
                if max(ws) - min(ws) > 0.01:
                    add("warn", rule, f"{text} 的宽度不一致")
                if max(hs) - min(hs) > 0.01:
                    add("warn", rule, f"{text} 的高度不一致")
                ys = sorted((r[1] for r in rs), reverse=True)
                gaps = [ys[k] - ys[k + 1] for k in range(len(ys) - 1)]
                if gaps and max(gaps) - min(gaps) > 0.01:
                    add("warn", rule, f"{text} 的面板间距不一致")

    _group_check("行标签", shared.get("row_labels") or [], "C10")
    _group_check("列标签", shared.get("column_labels") or [], "C11")

    # 自动对齐：共享顶边应等高，共享左边应等宽
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            n1, x1, y1, w1, h1 = rects[i]
            n2, x2, y2, w2, h2 = rects[j]
            if abs((y1 + h1) - (y2 + h2)) < 0.004 and abs(h1 - h2) > 0.01:
                add("warn", "C12", f"{n1} 与 {n2} 顶边对齐但高度不一致")
            if abs(x1 - x2) < 0.004 and abs(w1 - w2) > 0.01:
                add("warn", "C12", f"{n1} 与 {n2} 左边对齐但宽度不一致")

    return issues


def compose(layout: dict, out: Path, strict: bool = False) -> None:
    issues = layout_lint(layout)
    fails = [i for i in issues if i["level"] == "fail"]
    warns = [i for i in issues if i["level"] == "warn"]
    print(f"[layout] {'FAIL' if fails else ('WARN' if warns else 'PASS')}"
          f"  fail={len(fails)} warn={len(warns)}")
    for i in issues:
        print(f"  [{i['level']}] {i['rule']} {i['msg']}")
    out.parent.mkdir(parents=True, exist_ok=True)
    (out.parent / (out.name + ".lint.txt")).write_text(
        "\n".join(f"[{i['level']}] {i['rule']} {i['msg']}" for i in issues) or "PASS",
        encoding="utf-8")
    if strict and fails:
        raise SystemExit("layout lint failed")

    W, H = layout.get("canvas", [10.0, 8.95])
    fig = plt.figure(figsize=(W, H))
    ov = fig.add_axes([0, 0, 1, 1])
    ov.set_xlim(0, 1)
    ov.set_ylim(0, 1)
    ov.axis("off")
    for c in layout.get("containers", []):
        x, y, w, h = c["rect"]
        ax = fig.add_axes([x + 0.008, y + 0.012, w - 0.016, h - 0.05])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        REG[c["panel"]](ax, c.get("spec"))
        color = c.get("color", "#2E9E4F")
        ov.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.002,rounding_size=0.008",
                                    fill=False, edgecolor=color, lw=1.6, ls=(0, (5, 3))))
        ov.text(x + 0.004, y + h - 0.012, c.get("letter", ""), fontsize=9,
                fontweight="bold", color=color, va="top")
        if c.get("title"):
            ov.text(x + 0.020, y + h - 0.012, c["title"], fontsize=6.5, va="top")

    # ---------------- 共享元素 ----------------
    shared = layout.get("shared") or {}
    by_letter = {c.get("letter"): c["rect"] for c in layout.get("containers", [])
                 if c.get("letter")}

    for cb in shared.get("colorbars", []):
        rs = [by_letter[p] for p in cb.get("panels", []) if p in by_letter]
        if not rs:
            continue
        x0 = min(r[0] for r in rs)
        x1 = max(r[0] + r[2] for r in rs)
        y0 = min(r[1] for r in rs)
        y1 = max(r[1] + r[3] for r in rs)
        rng = cb.get("range", [0, 1])
        placement = cb.get("placement", "right")
        if placement == "right":
            rect = [min(0.986, x1 + 0.012), y0, 0.010, y1 - y0]
        elif placement == "left":
            rect = [max(0.002, x0 - 0.022), y0, 0.010, y1 - y0]
        elif placement == "bottom":
            rect = [x0, max(0.002, y0 - 0.035), x1 - x0, 0.010]
        else:
            rect = [x0, min(0.992, y1 + 0.018), x1 - x0, 0.010]
        cax = fig.add_axes(rect)
        cmap = cb.get("cmap", "Blues")
        if placement in ("right", "left"):
            cax.imshow(np.linspace(rng[0], rng[1], 256).reshape(-1, 1),
                       aspect="auto", cmap=cmap, origin="lower")
            cax.set_xticks([])
            ticks = cb.get("ticks") or [rng[0], (rng[0] + rng[1]) / 2, rng[1]]
            cax.set_yticks(np.linspace(0, 255, len(ticks)))
            cax.set_yticklabels([f"{t:g}" for t in ticks], fontsize=5)
            cax.set_ylabel(cb.get("label", ""), fontsize=6, labelpad=2)
        else:
            cax.imshow(np.linspace(rng[0], rng[1], 256).reshape(1, -1),
                       aspect="auto", cmap=cmap, origin="lower")
            cax.set_yticks([])
            ticks = cb.get("ticks") or [rng[0], (rng[0] + rng[1]) / 2, rng[1]]
            cax.set_xticks(np.linspace(0, 255, len(ticks)))
            cax.set_xticklabels([f"{t:g}" for t in ticks], fontsize=5)
            cax.set_xlabel(cb.get("label", ""), fontsize=6, labelpad=1)
        cax.tick_params(length=2, width=0.5, pad=1)

    for rl in shared.get("row_labels", []):
        rs = [by_letter[p] for p in rl.get("panels", []) if p in by_letter]
        if not rs:
            continue
        x = min(r[0] for r in rs)
        yc = (min(r[1] for r in rs) + max(r[1] + r[3] for r in rs)) / 2
        ov.text(x - 0.035, yc, rl.get("text", ""), rotation=90, ha="center",
                va="center", fontsize=7)

    for cl in shared.get("column_labels", []):
        rs = [by_letter[p] for p in cl.get("panels", []) if p in by_letter]
        if not rs:
            continue
        xc = (min(r[0] for r in rs) + max(r[0] + r[2] for r in rs)) / 2
        y = max(r[1] + r[3] for r in rs)
        ov.text(xc, y + 0.008, cl.get("text", ""), ha="center", va="bottom", fontsize=7)

    out.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(out.with_suffix(f".{ext}"), dpi=300)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p = sub.add_parser("demo")
    p.add_argument("--out", default="figures/repro/panels_contact.png")
    p = sub.add_parser("compose")
    p.add_argument("--layout", required=True)
    p.add_argument("--out", default="figures/repro/composite")
    p.add_argument("--strict", action="store_true")
    p = sub.add_parser("lint")
    p.add_argument("--layout", required=True)
    args = ap.parse_args()

    if args.cmd == "list":
        for name in REG:
            print(name)
    elif args.cmd == "demo":
        demo(Path(args.out))
        print(args.out)
    elif args.cmd == "lint":
        layout = json.loads(Path(args.layout).read_text(encoding="utf-8"))
        issues = layout_lint(layout)
        for i in issues:
            print(f"[{i['level']}] {i['rule']} {i['msg']}")
        if not issues:
            print("PASS")
    else:
        compose(json.loads(Path(args.layout).read_text(encoding="utf-8")), Path(args.out), args.strict)
        print(args.out)


if __name__ == "__main__":
    main()
