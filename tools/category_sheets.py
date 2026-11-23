"""按类型抽取图表，生成类别拼版，供人工/模型观察"精美"的共性。

用法：
  py tools/category_sheets.py --per 6
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus" / "figures" / "corpus"
OUT = CORPUS / "category_sheets"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per", type=int, default=6)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    man = {}
    for line in (CORPUS / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            man.setdefault(r["file"], r)

    labels = {}
    for fn in ("labels.csv", "labels_arxiv.csv"):
        p = CORPUS / fn
        if p.exists():
            for r in csv.DictReader(p.open(encoding="utf-8-sig")):
                if r["label"].strip():
                    labels[r["file"]] = r["label"].strip()

    groups = defaultdict(list)
    for f, lab in labels.items():
        if (ROOT / f).exists():
            groups[lab].append(f)

    OUT.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    for lab, files in groups.items():
        random.Random(args.seed).shuffle(files)
        pick = files[: args.per]
        if not pick:
            continue
        cols, rows = 3, 2
        tw, th = 420, 320
        canvas = Image.new("RGB", (cols * tw, rows * th + 34), "white")
        d = ImageDraw.Draw(canvas)
        d.text((8, 6), f"{lab}  (n={len(files)})", fill="#222", font=font)
        for i, f in enumerate(pick):
            im = Image.open(ROOT / f).convert("RGB")
            im.thumbnail((tw - 10, th - 10))
            x = (i % cols) * tw + (tw - im.width) // 2
            y = (i // cols) * th + 34 + (th - im.height) // 2
            canvas.paste(im, (x, y))
        path = OUT / f"{lab}.png"
        canvas.save(path)
        print(path, len(pick), "/", len(files))


if __name__ == "__main__":
    main()
