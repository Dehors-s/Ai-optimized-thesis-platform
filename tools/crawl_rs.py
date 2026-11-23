"""抓取《测绘学报》遥感/测绘文章（沿“下一篇”链式遍历）。

用法：py tools/crawl_rs.py --limit 500 --start 12500
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
MANIFEST = CORPUS / "manifest.jsonl"
LOG = CORPUS / "crawl_rs.log"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
BASE = "http://xb.chinasmp.com/CN/abstract/abstract{id}.shtml"


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        print(line.encode("gbk", "replace").decode("gbk"), flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def meta(soup: BeautifulSoup, name: str) -> str:
    for m in soup.find_all("meta"):
        if (m.get("name") or "") == name:
            return (m.get("content") or "").strip()
    return ""


def extract(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    m = re.search(r"摘\s*要\s*[:：]?\s*([\u4e00-\u9fff].{80,1500}?)(?:关键\s*词|关键字)", text)
    abstract = m.group(1).strip() if m else ""
    doi = meta(soup, "citation_doi")
    year = ""
    ym = re.search(r"AGCS\.(\d{4})", doi) or re.search(r"AGCS\.(\d{4})", text)
    if ym:
        year = ym.group(1)
    nxt = re.search(r'href="([^"]+)"[^>]*>\s*下一篇', html)
    return {
        "title": meta(soup, "citation_title"),
        "authors": meta(soup, "citation_authors"),
        "keywords": meta(soup, "citation_keywords"),
        "doi": doi,
        "year": year,
        "abstract": abstract,
        "next": nxt.group(1) if nxt else "",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--start", type=int, default=12500)
    ap.add_argument("--end", type=int, default=14100)
    ap.add_argument("--step", type=int, default=20)
    ap.add_argument("--delay", type=float, default=0.25)
    args = ap.parse_args()

    seen_urls, seen_doi = set(), set()
    if MANIFEST.exists():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
                seen_urls.add(r["url"])
                if r.get("doi"):
                    seen_doi.add(r["doi"])
            except Exception:
                pass

    s = requests.Session()
    s.trust_env = False
    s.headers.update({"User-Agent": UA})
    done = 0
    visited: set[str] = set()
    log(f"start seeds {args.start}..{args.end} step {args.step} seen={len(seen_urls)}")

    for seed in range(args.start, args.end, args.step):
        if done >= args.limit:
            break
        url = BASE.format(id=seed)
        while url and done < args.limit and url not in visited:
            visited.add(url)
            try:
                resp = s.get(url, timeout=30)
                html = resp.content.decode("utf-8", errors="ignore")
            except Exception as e:
                log(f"ERR {url} {type(e).__name__}")
                break
            rec = extract(html)
            if rec["abstract"] and len(rec["abstract"]) >= 80 and rec["doi"] not in seen_doi:
                rec.update({
                    "id": hashlib.sha1(url.encode()).hexdigest()[:12],
                    "url": url,
                    "journal": "测绘学报",
                })
                with MANIFEST.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                seen_doi.add(rec["doi"])
                done += 1
                if done % 25 == 0:
                    log(f"done={done} year={rec['year']} last={rec['title'][:24]}")
            nxt = rec["next"]
            if not nxt or nxt == url:
                break
            url = nxt
            time.sleep(args.delay)

    log(f"finish done={done}")


if __name__ == "__main__":
    main()
