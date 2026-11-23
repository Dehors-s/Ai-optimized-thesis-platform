"""SN-MSU 架构图（SVG，Edge 无头渲染）：3D 特征块 + 分区 + 模块放大。"""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICON = ROOT / "assets" / "icons"
PROJ = ROOT / "projects" / "双高2026" / "figures"
SVG = PROJ / "fig5_snmsu.svg"
PNG = PROJ / "fig5_snmsu.png"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
FONT = "Microsoft YaHei, Noto Sans CJK SC, sans-serif"


def icon(name: str, x: float, y: float, size: float = 18) -> str:
    b64 = base64.b64encode((ICON / f"{name}.svg").read_bytes()).decode()
    return (f'<image x="{x}" y="{y}" width="{size}" height="{size}" '
            f'href="data:image/svg+xml;base64,{b64}"/>')


DEFS = """
<defs>
  <linearGradient id="blue" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#7FA9D9"/><stop offset="1" stop-color="#2F6DB3"/></linearGradient>
  <linearGradient id="lblue" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#C9DDF2"/><stop offset="1" stop-color="#8FB6DD"/></linearGradient>
  <linearGradient id="orange" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#F2B37A"/><stop offset="1" stop-color="#D9772B"/></linearGradient>
  <linearGradient id="green" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#9CCB9C"/><stop offset="1" stop-color="#5A9E5A"/></linearGradient>
  <linearGradient id="purple" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#B49ACB"/><stop offset="1" stop-color="#7E5AA8"/></linearGradient>
  <linearGradient id="red" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#D9887E"/><stop offset="1" stop-color="#B03A2E"/></linearGradient>
  <linearGradient id="gray" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#E6E6E6"/><stop offset="1" stop-color="#C9C9C9"/></linearGradient>
  <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
    <path d="M0,0 L10,5 L0,10 z" fill="#555"/></marker>
  <filter id="sh" x="-20%" y="-20%" width="140%" height="140%">
    <feDropShadow dx="1" dy="2" stdDeviation="2" flood-opacity="0.12"/></filter>
</defs>
"""


def cube(x, y, w, h, dx, dy, grad, lines=(), fs=12):
    top = f"{x},{y} {x+dx},{y-dy} {x+w+dx},{y-dy} {x+w},{y}"
    side = f"{x+w},{y} {x+w+dx},{y-dy} {x+w+dx},{y+h-dy} {x+w},{y+h}"
    out = ['<g filter="url(#sh)">',
           f'<polygon points="{top}" fill="{grad}" opacity="0.72"/>',
           f'<polygon points="{side}" fill="{grad}" opacity="0.50"/>',
           f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#{grad})" '
           f'stroke="rgba(255,255,255,.7)" stroke-width="0.8"/>', "</g>"]
    for i, ln in enumerate(lines):
        cy = y + h / 2 + (i - (len(lines) - 1) / 2) * (fs + 3)
        out.append(f'<text x="{x+w/2}" y="{cy+fs*0.35}" font-family="{FONT}" font-size="{fs}" '
                   f'text-anchor="middle" fill="#fff">{ln}</text>')
    return "".join(out)


def txt(x, y, s, fs=13, color="#222", anchor="start", weight="normal"):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{fs}" fill="{color}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{s}</text>')


def arrow(x1, y1, x2, y2, color="#555", w=1.2, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{w}"{d} marker-end="url(#arr)"/>')


def main():
    W, H = 1280, 640
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         DEFS, f'<rect width="{W}" height="{H}" fill="white"/>']

    s.append('<rect x="4" y="4" width="888" height="632" rx="12" fill="#F5F8FD" stroke="#DCE7F4"/>')
    s.append('<rect x="900" y="4" width="180" height="632" rx="12" fill="#FFF9F2" stroke="#F2DDC8"/>')
    s.append('<rect x="1088" y="4" width="188" height="632" rx="12" fill="#F4FAF5" stroke="#D8EBD9"/>')
    s.append(txt(20, 34, "a  SN-MSU 整体结构", 16, "#2F6DB3", weight="bold"))
    s.append(txt(916, 34, "b  DRB（/8）", 15, "#D9772B", weight="bold"))
    s.append(txt(1104, 34, "c  SARA（/16）", 15, "#5A9E5A", weight="bold"))

    # 输入
    s.append(cube(28, 96, 64, 58, 20, 16, "gray", ["HSI"], 14))
    s.append(txt(60, 178, "dual 346×512²", 10, "#555", "middle"))
    s.append(icon("wave-sine", 30, 184, 18))
    s.append(txt(52, 198, "谱形 + 统计", 9, "#777"))
    s.append(arrow(112, 124, 132, 124))
    s.append(cube(136, 96, 58, 48, 12, 10, "purple", ["1×1"], 13))
    s.append(txt(165, 162, "346→128", 10, "#7E5AA8", "middle"))
    s.append(icon("layers-subtract", 154, 168, 16))
    s.append(arrow(196, 120, 214, 120))

    # 编码器
    enc = [
        (216, 96, 62, 46, 14, 12, "blue", "128", "512²", "#2F6DB3"),
        (274, 170, 56, 42, 18, 14, "blue", "256", "256²", "#2F6DB3"),
        (332, 244, 50, 38, 22, 16, "blue", "512", "128²", "#2F6DB3"),
        (390, 318, 44, 34, 26, 18, "orange", "896", "64²", "#D9772B"),
        (448, 392, 38, 30, 18, 14, "green", "448", "32²", "#5A9E5A"),
    ]
    for x, y, w, h, dx, dy, g, ch, res, col in enc:
        s.append(cube(x, y, w, h, dx, dy, g, [ch], 12))
        s.append(txt(x + w / 2, y + h + 18, res, 9, col, "middle"))
    s.append(arrow(278, 142, 288, 168))
    s.append(arrow(336, 216, 346, 242))
    s.append(arrow(394, 290, 404, 316))
    s.append(arrow(452, 364, 462, 390))

    # 解码器
    dec = [
        (528, 318, 46, 34, 20, 14, "lblue", "896", "cat e5+e4"),
        (586, 244, 52, 38, 18, 14, "lblue", "512", "cat e3"),
        (644, 170, 58, 42, 16, 12, "lblue", "256", "cat e2"),
        (702, 96, 62, 46, 14, 12, "lblue", "128", "cat e1"),
    ]
    for x, y, w, h, dx, dy, g, ch, cat in dec:
        s.append(cube(x, y, w, h, dx, dy, g, [ch], 12))
        s.append(txt(x + w / 2, y + h + 18, cat, 8, "#4A6F9C", "middle"))
    s.append(arrow(576, 352, 588, 326))
    s.append(arrow(634, 278, 646, 252))
    s.append(arrow(702, 204, 712, 178))

    # skip
    s.append(arrow(280, 88, 700, 88, "#9A9A9A", 1.0, "4 3"))
    s.append(arrow(334, 162, 642, 162, "#9A9A9A", 1.0, "4 3"))
    s.append(arrow(388, 236, 584, 236, "#9A9A9A", 1.0, "4 3"))
    s.append(arrow(442, 310, 526, 310, "#9A9A9A", 1.0, "4 3"))
    s.append(arrow(488, 386, 528, 336, "#9A9A9A", 1.0, "4 3"))

    # 头与输出
    s.append(arrow(770, 120, 788, 120))
    s.append(cube(792, 100, 46, 40, 10, 8, "red", ["1×1"], 12))
    s.append(txt(815, 156, "31 类", 9, "#B03A2E", "middle"))
    s.append('<g filter="url(#sh)"><rect x="846" y="100" width="40" height="40" fill="#fff" stroke="#CCC"/></g>')
    colors = ["#6BAF6B", "#D9A441", "#4E79A7", "#C75B4A", "#8E6BB0", "#67A9A3",
              "#B7C85A", "#D98C6B", "#6C8EBF", "#A3B18A"]
    for yy in range(4):
        for xx in range(4):
            s.append(f'<rect x="{848+xx*9.4}" y="{102+yy*9.4}" width="9.4" height="9.4" '
                     f'fill="{colors[(xx*4+yy)%len(colors)]}" opacity="0.9"/>')
    s.append(txt(866, 158, "分类图", 8, "#777", "middle"))

    # 底部注释
    s.append(txt(28, 500, "空间尺寸  512² → 256² → 128² → 64² → 32²", 11, "#6B7A90"))
    s.append(txt(28, 530, "参数 5,015,711 · 通道 128/256/512/896 · /16 半宽 448 · 上采样 nearest",
                 11, "#555"))
    s.append(icon("stack-2", 28, 548, 16))
    s.append(txt(50, 561, "17 个 SN-MSU 成员之一；单体定点口径 0.6087", 10, "#777"))

    # DRB 面板
    for yy, d in [(92, 1), (172, 2), (252, 3)]:
        s.append(cube(916, yy, 48, 38, 9, 7, "orange", [], 10))
        s.append(txt(940, yy - 8, f"d={d}", 10, "#A06020", "middle"))
        for k in range(5):
            s.append(f'<line x1="{924+k*8}" y1="{yy+8}" x2="{924+k*8}" y2="{yy+30}" '
                     f'stroke="#fff" stroke-width="1.2" opacity="0.55"/>')
    s.append('<rect x="978" y="100" width="10" height="190" rx="4" fill="#E8A66A"/>')
    s.append('<text x="983" y="210" font-family="Microsoft YaHei" font-size="9" fill="#fff" '
             'text-anchor="middle" transform="rotate(-90 983 210)">fold</text>')
    for yy in (111, 191, 271):
        s.append(arrow(966, yy, 977, yy, "#A06020", 1.0))
    s.append(arrow(988, 195, 1004, 195, "#A06020", 1.2))
    s.append(cube(1006, 172, 56, 46, 12, 10, "orange", ["7×7"], 11))
    s.append(txt(1034, 234, "等效 depthwise", 9, "#8A4B16", "middle"))
    s.append(txt(916, 320, "并行 depthwise → 推理折叠", 10, "#8A4B16"))
    s.append(txt(916, 340, "零额外开销；ERF ≈ 60 px", 10, "#8A4B16"))
    s.append(icon("arrows-split-2", 916, 352, 18))

    # SARA 面板
    s.append(cube(1104, 90, 46, 36, 9, 7, "green", ["q/k/v"], 9))
    s.append(cube(1104, 154, 46, 36, 9, 7, "green", ["DW3×3"], 9))
    s.append(arrow(1156, 108, 1186, 108, "#3F7F3F", 1.0))
    s.append(arrow(1156, 172, 1186, 172, "#3F7F3F", 1.0))
    s.append('<g filter="url(#sh)"><rect x="1188" y="90" width="68" height="68" fill="#fff" stroke="#B9D8BA"/></g>')
    for yy in range(6):
        for xx in range(6):
            op = 0.12 + 0.85 * (1 - abs(xx - yy) / 6)
            s.append(f'<rect x="{1190+xx*11}" y="{92+yy*11}" width="10.5" height="10.5" '
                     f'fill="#5A9E5A" opacity="{op:.2f}"/>')
    s.append(txt(1222, 174, "softmax(QKᵀ/τ)", 8, "#3F7F3F", "middle"))
    s.append(cube(1104, 220, 60, 30, 8, 6, "green", ["门控 γ"], 9))
    s.append(arrow(1134, 190, 1134, 218, "#3F7F3F", 1.0))
    s.append(txt(1104, 282, "内容相关亲和", 10, "#3F7F3F"))
    s.append(txt(1104, 302, "迭代 2 次", 10, "#3F7F3F"))
    s.append(txt(1104, 322, "零初始化门控", 10, "#3F7F3F"))
    s.append(txt(1104, 342, "4 MB/样本", 10, "#3F7F3F"))
    s.append(icon("focus-2", 1104, 356, 18))

    s.append("</svg>")
    PROJ.mkdir(parents=True, exist_ok=True)
    SVG.write_text("".join(s), encoding="utf-8")
    uri = "file:///" + str(SVG).replace("\\", "/").replace(" ", "%20")
    subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--window-size=1280,640", "--force-device-scale-factor=2",
                    f"--screenshot={PNG}", uri], capture_output=True)
    print(PNG)


if __name__ == "__main__":
    main()
