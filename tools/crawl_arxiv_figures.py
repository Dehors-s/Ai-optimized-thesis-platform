"""从 arXiv 批量抓图表（HTML 版），补充语料。

用法：
  py tools/crawl_arxiv_figures.py --query 'all:"hyperspectral" AND cat:cs.CV' --papers 25
  py tools/crawl_arxiv_figures.py --query 'all:"remote sensing" AND cat:cs.CV' --papers 25

产物：
  corpus/figures/corpus/arxiv/{id}-f{n}.png
  manifest.jsonl 追加记录
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("FIGCORPUS_OUT", ROOT / "corpus" / "figures" / "corpus"))
if not OUT.is_absolute():
    OUT = ROOT / OUT
MANIFEST = OUT / "manifest.jsonl"
UA = {"User-Agent": "Mozilla/5.0 paperkit-arxivfig/1.0"}


def get(url: str, timeout: int = 40) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def strip(s: str) -> str:
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def save(url: str, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(["curl.exe", "-L", "--max-time", "40", "-s",
                        "-A", UA["User-Agent"], "-o", str(path), url], capture_output=True)
    if p.returncode != 0 or not path.exists() or path.stat().st_size < 5000:
        path.unlink(missing_ok=True)
        raise ValueError("download failed")
    return path.stat().st_size


def append(rec: dict) -> None:
    with MANIFEST.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def search(q: str, n: int) -> list[str]:
    url = ("http://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(q)
           + f"&start=0&max_results={n}&sortBy=submittedDate&sortOrder=descending")
    raw = get(url, 60)
    ids = re.findall(r"<id>http://arxiv.org/abs/([^<]+)</id>", raw)
    return [i.split("v")[0] for i in ids]


def crawl(aid: str, max_figs: int = 3) -> int:
    page = ""
    for u in (f"https://arxiv.org/html/{aid}", f"https://ar5iv.labs.arxiv.org/html/{aid}"):
        try:
            page = get(u)
            if "<figure" in page:
                base = u
                break
        except Exception:  # noqa: BLE001
            continue
    if not page or "<figure" not in page:
        return 0
    title = strip((re.search(r"(?is)<h1[^>]*>(.*?)</h1>", page) or [None, ""])[1])[:120]
    n = 0
    for k, block in enumerate(re.findall(r"(?is)<figure\b.*?</figure>", page), 1):
        if n >= max_figs:
            break
        cap = strip((re.search(r"(?is)<figcaption[^>]*>(.*?)</figcaption>", block) or [None, ""])[1])
        img = re.search(r'<img[^>]+src="([^"]+)"', block)
        if not cap or not img:
            continue
        src = urllib.parse.urljoin(base, img.group(1))
        path = OUT / "arxiv" / f"{aid}-f{k}.png"
        rec = {"source": "arxiv", "journal": "arxiv", "arxiv": aid, "title": title,
               "fig": k, "file": str(path.relative_to(ROOT)), "caption": cap}
        if path.exists() and path.stat().st_size > 5000:
            rec["bytes"] = path.stat().st_size
            append(rec)
            n += 1
            continue
        try:
            rec["bytes"] = save(src, path)
        except Exception:  # noqa: BLE001
            continue
        append(rec)
        n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--papers", type=int, default=25)
    ap.add_argument("--figs", type=int, default=3)
    args = ap.parse_args()

    ids = search(args.query, args.papers)
    print("papers", len(ids), flush=True)
    total = 0
    for i, aid in enumerate(ids, 1):
        got = crawl(aid, args.figs)
        total += got
        print(f"{i}/{len(ids)} {aid} figs={got}", flush=True)
    print("total", total)


if __name__ == "__main__":
    main()
