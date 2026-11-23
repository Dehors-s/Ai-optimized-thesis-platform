"""并发抓取图表语料：Copernicus（GMD/ESSD/NHESS）+ arXiv。

用法：
  py tools/crawl_fast.py --journal gmd essd nhess --articles 20 --workers 10
  py tools/crawl_fast.py --arxiv 'all:"hyperspectral" AND cat:cs.CV' --papers 40 --workers 10
  py tools/crawl_fast.py --all --articles 20 --papers 40

产物：
  corpus/figures/corpus/{journal}/...
  corpus/figures/corpus/manifest.jsonl
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import html
import json
import os
import re
import subprocess
import sys
import threading
import urllib.parse
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("FIGCORPUS_OUT", ROOT / "corpus" / "figures" / "corpus"))
if not OUT.is_absolute():
    OUT = ROOT / OUT
MANIFEST = OUT / "manifest.jsonl"
UA = "Mozilla/5.0 paperkit-fastcrawl/1.0"

COP = {
    "gmd": ("Geoscientific Model Development", "gmd"),
    "essd": ("Earth System Science Data", "essd"),
    "nhess": ("Natural Hazards and Earth System Sciences", "nhess"),
    "tc": ("The Cryosphere", "tc"),
    "bg": ("Biogeosciences", "bg"),
    "hess": ("Hydrology and Earth System Sciences", "hess"),
}

lock = threading.Lock()
records: list[dict] = []


def curl_text(url: str, timeout: int = 30) -> str:
    p = subprocess.run(["curl.exe", "-L", "--max-time", str(timeout), "-s",
                        "-A", UA, url], capture_output=True)
    return p.stdout.decode("utf-8", "ignore") if p.stdout else ""


def curl_save(url: str, path: Path, timeout: int = 40) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    p = subprocess.run(["curl.exe", "-L", "--max-time", str(timeout), "-s",
                        "-A", UA, "-o", str(tmp), url], capture_output=True)
    if p.returncode != 0 or not tmp.exists() or tmp.stat().st_size < 5000:
        tmp.unlink(missing_ok=True)
        raise ValueError("bad download")
    tmp.replace(path)
    return path.stat().st_size


def strip(s: str) -> str:
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def record(rec: dict) -> None:
    with lock:
        records.append(rec)


def existing() -> set[str]:
    if not MANIFEST.exists():
        return set()
    return {json.loads(l)["file"] for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()}


def crossref(container: str, rows: int) -> list[str]:
    q = urllib.parse.quote(f"container-title:{container},from-pub-date:2025-01-01,type:journal-article")
    raw = curl_text(f"https://api.crossref.org/works?filter={q}&rows={rows}&select=DOI", 40)
    try:
        return [x["DOI"] for x in json.loads(raw)["message"]["items"]]
    except Exception:  # noqa: BLE001
        return []


def crawl_journal(key: str, articles: int, workers: int) -> None:
    name, code = COP[key]
    dois = crossref(name, articles)
    print(f"{key}: {len(dois)} articles", flush=True)
    jobs = []
    for doi in dois:
        m = re.match(rf"10\.5194/{code}-(\d+)-(\d+)-(\d+)", doi)
        if not m:
            continue
        vol, page, year = m.groups()
        url = f"https://{code}.copernicus.org/articles/{vol}/{page}/{year}/"
        jobs.append((url, code, doi))
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(lambda j: _safe_article(*j), jobs))


def _safe_article(url: str, code: str, doi: str) -> None:
    parts = url.rstrip("/").split("/")
    vol, page, year = parts[-3], parts[-2], parts[-1]
    page_html = curl_text(url)
    for k, block in enumerate(re.split(r'(?is)<div class="fig"', page_html)[1:], 1):
        img = re.search(r'data-webversion="([^"]+)"', block) or re.search(r'href="([^"]+\.png)"', block)
        cap = strip((re.search(r'(?is)<div class="caption">(.*?)</div>', block) or [None, ""])[1])
        if not img or not cap:
            continue
        path = OUT / code / f"{doi.replace('/', '_')}-f{k:02d}.png"
        try:
            size = curl_save(img.group(1), path)
        except Exception:  # noqa: BLE001
            continue
        record({"source": "copernicus", "journal": code, "doi": doi, "url": url, "fig": k,
                "file": str(path.relative_to(ROOT)), "caption": cap, "bytes": size})


def arxiv_ids(query: str, n: int) -> list[str]:
    raw = curl_text("http://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(query)
                    + f"&start=0&max_results={n}&sortBy=submittedDate&sortOrder=descending", 60)
    return [i.split("v")[0] for i in re.findall(r"<id>http://arxiv.org/abs/([^<]+)</id>", raw)]


def arxiv_one(aid: str, figs: int = 3) -> None:
    page, base = "", ""
    for u in (f"https://arxiv.org/html/{aid}", f"https://ar5iv.labs.arxiv.org/html/{aid}"):
        page = curl_text(u, 25)
        if "<figure" in page:
            base = u
            break
    if "<figure" not in page:
        return
    n = 0
    for k, block in enumerate(re.findall(r"(?is)<figure\b.*?</figure>", page), 1):
        if n >= figs:
            break
        cap = strip((re.search(r"(?is)<figcaption[^>]*>(.*?)</figcaption>", block) or [None, ""])[1])
        img = re.search(r'<img[^>]+src="([^"]+)"', block)
        if not cap or not img:
            continue
        src = urllib.parse.urljoin(base, img.group(1))
        path = OUT / "arxiv" / f"{aid}-f{k}.png"
        try:
            size = curl_save(src, path, 30)
        except Exception:  # noqa: BLE001
            continue
        record({"source": "arxiv", "journal": "arxiv", "arxiv": aid, "fig": k,
                "file": str(path.relative_to(ROOT)), "caption": cap, "bytes": size})
        n += 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", nargs="*", default=[])
    ap.add_argument("--articles", type=int, default=15)
    ap.add_argument("--arxiv", default="")
    ap.add_argument("--papers", type=int, default=30)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    ledgers = existing()
    OUT.mkdir(parents=True, exist_ok=True)
    journals = list(COP) if args.all else args.journal
    for key in journals:
        try:
            crawl_journal(key, args.articles, args.workers)
        except Exception as e:  # noqa: BLE001
            print("journal fail", key, e, flush=True)

    queries = [args.arxiv] if args.arxiv else []
    if args.all:
        queries = ['all:"hyperspectral" AND cat:cs.CV', 'all:"remote sensing" AND cat:cs.CV']
    for q in queries:
        ids = arxiv_ids(q, args.papers)
        print("arxiv", q, len(ids), flush=True)
        with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
            list(ex.map(arxiv_one, ids))

    new = [r for r in records if r["file"] not in ledgers]
    with MANIFEST.open("a", encoding="utf-8") as f:
        for r in new:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"records {len(new)} (total seen {len(ledgers) + len(new)})", flush=True)


if __name__ == "__main__":
    main()
