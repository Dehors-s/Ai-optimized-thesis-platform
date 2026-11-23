"""把图表语料的英文图注翻译成中文，缓存到 captions_zh.json。

用法：
  py tools/translate_captions.py
  py tools/translate_captions.py --limit 10

数据源：MyMemory 公共翻译接口（免费、无需 key）。只翻图注首段，控制长度。
失败会保留空串，标注页回退显示英文。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus" / "figures" / "corpus"
MANIFEST = CORPUS / "manifest.jsonl"
CACHE = CORPUS / "captions_zh.json"


def translate(text: str) -> str:
    q = urllib.parse.quote(text[:420])
    url = f"https://api.mymemory.translated.net/get?q={q}&langpair=en|zh-CN"
    p = subprocess.run(["curl.exe", "-L", "--max-time", "40", "-s", url],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    try:
        data = json.loads(p.stdout)
        if data.get("responseStatus") == 200:
            return data.get("responseData", {}).get("translatedText", "").strip()
    except Exception:  # noqa: BLE001
        pass
    return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--journal", default="", help="只翻某个期刊，如 arxiv")
    args = ap.parse_args()

    rows, seen = [], set()
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r["file"] in seen:
            continue
        seen.add(r["file"])
        rows.append(r)
    if args.journal:
        rows = [r for r in rows if r.get("journal") == args.journal]
    if args.limit:
        rows = rows[: args.limit]

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    todo = [r for r in rows if not cache.get(r["file"])]
    print(f"待翻译 {len(todo)} / {len(rows)}")

    for i, r in enumerate(todo, 1):
        zh = translate(r.get("caption", ""))
        cache[r["file"]] = zh
        print(f"{i:03d}/{len(todo)} {'ok' if zh else 'FAIL'} | {zh[:60]}")
        if i % 10 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(0.5)

    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for r in rows if cache.get(r["file"]))
    print(f"完成 {ok}/{len(rows)} → {CACHE}")


if __name__ == "__main__":
    main()
