"""合并分片抓取的图表语料。

用法：
  py tools/merge_corpora.py --parts corpus_p1 corpus_p2 corpus_p3 corpus_p4
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "corpus" / "figures"
FINAL = BASE / "corpus"
MANIFEST = FINAL / "manifest.jsonl"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", nargs="+", required=True)
    args = ap.parse_args()

    FINAL.mkdir(parents=True, exist_ok=True)
    seen = set()
    if MANIFEST.exists():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            if line.strip():
                seen.add(json.loads(line)["file"])

    with MANIFEST.open("a", encoding="utf-8") as out:
        for part in args.parts:
            pdir = BASE / part
            if not pdir.exists():
                print("skip", part)
                continue
            for jdir in pdir.iterdir():
                if not jdir.is_dir():
                    continue
                dst_dir = FINAL / jdir.name
                dst_dir.mkdir(parents=True, exist_ok=True)
                for f in jdir.iterdir():
                    if not f.is_file():
                        continue
                    dst = dst_dir / f.name
                    if not dst.exists():
                        shutil.move(str(f), str(dst))
            man = pdir / "manifest.jsonl"
            if man.exists():
                for line in man.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    r = json.loads(line)
                    r["file"] = r["file"].replace(part, "corpus")
                    if r["file"] in seen:
                        continue
                    seen.add(r["file"])
                    out.write(json.dumps(r, ensure_ascii=False) + "\n")
            print("merged", part)
    print("manifest entries", len(seen))


if __name__ == "__main__":
    main()
