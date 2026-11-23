"""抓取中文期刊摘要/PDF，构建语料库（遥感 + 计算机）。

用法：
  py tools/crawl_corpus.py --max-articles 900 --max-pdf-mb 300 --delay 0.25
输出：
  corpus/manifest.jsonl   每篇一条（含摘要）
  corpus/pdf/<journal>/   下载的 PDF
  corpus/text/<journal>/  PDF 抽取的纯文本
  corpus/crawl.log
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import pymupdf
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
MANIFEST = CORPUS / "manifest.jsonl"
LOG = CORPUS / "crawl.log"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

JOURNALS = {
    "aas": {
        "name": "自动化学报",
        "toc": "https://www.aas.net.cn/cn/article/{year}/{issue}",
        "link_re": r"//www\.aas\.net\.cn/cn/article/doi/(10\.16383/[^\"'?#]+)",
        "article": "https://www.aas.net.cn/cn/article/doi/{id}",
        "years": range(2022, 2027),
        "pdf": "https://www.aas.net.cn/cn/article/pdf/preview/{id}.pdf",
    },
    "jos": {
        "name": "软件学报",
        "toc": "https://www.jos.org.cn/jos/article/issue/{year}_{issue}",
        "link_re": r"/jos/article/abstract/(\d+)",
        "article": "https://www.jos.org.cn/jos/article/abstract/{id}",
        "years": range(2024, 2027),
        "pdf": None,
    },
}

XB_HOME = "http://xb.chinasmp.com/CN/1001-1595/home.shtml"
XB_RE = r"(?:https?://xb\.chinasmp\.com)?/?CN/(10\.11947/[^\"'?#]+)"
CJIG_SITEMAP = "https://www.cjig.cn/sitemap.txt"
CJIG_RE = r"https://www\.cjig\.cn/zh/article/doi/[^/\s]+/"
JOURNAL_NAMES = {
    "aas": "自动化学报",
    "jos": "软件学报",
    "xb": "测绘学报",
    "cjig": "中国图象图形学报",
}


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        print(line.encode("gbk", "replace").decode("gbk"), flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def make_session() -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    return s


def fetch(s: requests.Session, url: str, tries: int = 3) -> str | None:
    for k in range(tries):
        try:
            r = s.get(url, timeout=30)
            if r.status_code != 200:
                return None
            enc = r.encoding
            if not enc or enc.lower() in ("iso-8859-1", "ascii"):
                enc = r.apparent_encoding or "utf-8"
            return r.content.decode(enc, errors="ignore")
        except Exception:
            time.sleep(1.0 + k)
    return None


def meta(soup: BeautifulSoup, name: str) -> str:
    for m in soup.find_all("meta"):
        if (m.get("name") or "").lower() == name.lower():
            v = (m.get("content") or "").strip()
            if v:
                return v
    return ""


def clean_text(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def extract_abstract(soup: BeautifulSoup) -> str:
    # 1) 常见容器
    for sel in (
        "div.article-abstract",
        "div.article_abstract_main",
        "div#abstract",
        "section.abstract",
        "div.abstract",
    ):
        node = soup.select_one(sel)
        if node:
            t = clean_text(node.get_text(" ", strip=True))
            t = re.sub(r"^摘\s*要\s*[:：]?\s*", "", t)
            t = re.split(r"关键\s*词|关键字|Key\s*words", t)[0]
            if len(t) >= 80:
                return t.strip()
    # 2) 文本定位（要求冒号，避开搜索下拉框里的“摘要”）
    text = clean_text(soup.get_text(" ", strip=True))
    m = re.search(
        r"摘\s*要\s*[:：]\s*(.{80,2500}?)(?:关键\s*词|关键字|Key\s*words|参考文献)",
        text,
    )
    return m.group(1).strip() if m else ""


def extract(s: requests.Session, url: str) -> dict | None:
    html = fetch(s, url)
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")
    titles = [m.get("content", "").strip() for m in soup.find_all("meta")
              if (m.get("name") or "") == "citation_title"]
    title = next((t for t in titles if re.search(r"[\u4e00-\u9fff]", t)), titles[0] if titles else "")
    return {
        "url": url,
        "title": clean_text(title),
        "authors": clean_text(meta(soup, "citation_authors") or meta(soup, "citation_author")),
        "keywords": clean_text(meta(soup, "citation_keywords")),
        "doi": clean_text(meta(soup, "citation_doi")),
        "year": clean_text(meta(soup, "citation_date") or meta(soup, "citation_publication_date"))[:4],
        "abstract": extract_abstract(soup),
    }


def harvest(s: requests.Session, key: str) -> list[str]:
    cfg = JOURNALS[key]
    urls: list[str] = []
    for year in cfg["years"]:
        for issue in range(1, 13):
            page = fetch(s, cfg["toc"].format(year=year, issue=issue))
            if not page:
                continue
            ids = re.findall(cfg["link_re"], page)
            for i in dict.fromkeys(ids):
                urls.append(cfg["article"].format(id=i))
            time.sleep(0.1)
    return list(dict.fromkeys(urls))


def harvest_xb(s: requests.Session) -> list[str]:
    page = fetch(s, XB_HOME)
    if not page:
        return []
    ids = re.findall(XB_RE, page)
    return [f"http://xb.chinasmp.com/CN/{i}" for i in dict.fromkeys(ids)]


def harvest_cjig(s: requests.Session) -> list[str]:
    page = fetch(s, CJIG_SITEMAP)
    if not page:
        return []
    return list(dict.fromkeys(re.findall(CJIG_RE, page)))


def load_seen() -> set[str]:
    seen = set()
    if MANIFEST.exists():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            try:
                seen.add(json.loads(line)["url"])
            except Exception:
                pass
    return seen


def save_pdf(s: requests.Session, key: str, doi: str, rec: dict, budget: dict) -> None:
    cfg = JOURNALS[key]
    if not cfg.get("pdf") or not doi:
        return
    safe = re.sub(r"[^0-9A-Za-z._-]+", "_", doi)
    out = CORPUS / "pdf" / key / f"{safe}.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        rec["pdf_bytes"] = out.stat().st_size
    else:
        if budget["used"] > budget["cap"]:
            return
        try:
            r = s.get(cfg["pdf"].format(id=doi), timeout=60)
            if r.status_code != 200 or not r.content.startswith(b"%PDF"):
                return
            if len(r.content) < 30_000:
                return
            out.write_bytes(r.content)
            budget["used"] += len(r.content)
            rec["pdf_bytes"] = len(r.content)
        except Exception:
            return
    if not rec.get("pdf_bytes"):
        return
    try:
        doc = pymupdf.open(out)
        text = "\n".join(p.get_text() for p in doc)
        rec["pdf_pages"] = doc.page_count
        rec["text_chars"] = len(text)
        tp = CORPUS / "text" / key / f"{safe}.txt"
        tp.parent.mkdir(parents=True, exist_ok=True)
        tp.write_text(text, encoding="utf-8")
    except Exception:
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-articles", type=int, default=900)
    ap.add_argument("--max-pdf-mb", type=int, default=300)
    ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--delay", type=float, default=0.25)
    ap.add_argument("--only", default="aas,jos,xb")
    args = ap.parse_args()

    CORPUS.mkdir(parents=True, exist_ok=True)
    s = make_session()
    seen = load_seen()
    budget = {"cap": args.max_pdf_mb * 1024 * 1024, "used": 0}
    log(f"start: seen={len(seen)} cap={args.max_articles} pdf_cap={args.max_pdf_mb}MB")

    queues: list[tuple[str, str]] = []
    for key in [k.strip() for k in args.only.split(",") if k.strip()]:
        if key == "xb":
            urls = harvest_xb(s)
            log(f"xb harvested {len(urls)}")
        elif key == "cjig":
            urls = harvest_cjig(s)
            log(f"cjig harvested {len(urls)}")
        else:
            urls = harvest(s, key)
            log(f"{key} harvested {len(urls)}")
        queues += [(key, u) for u in urls]

    random.shuffle(queues)
    done = 0
    for key, url in queues:
        if done >= args.max_articles:
            break
        if url in seen:
            continue
        try:
            rec = extract(s, url)
        except Exception:
            rec = None
        if not rec or len(rec.get("abstract", "")) < 80:
            continue
        rec["id"] = hashlib.sha1(url.encode()).hexdigest()[:12]
        rec["journal"] = JOURNAL_NAMES.get(key, key)
        if key == "aas" and not args.no_pdf:
            save_pdf(s, key, rec.get("doi", ""), rec, budget)
        with MANIFEST.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        seen.add(url)
        done += 1
        if done % 20 == 0:
            log(f"done={done} pdf={budget['used']/1e6:.0f}MB last={rec['title'][:24]}")
        time.sleep(args.delay)
    log(f"finish: done={done} pdf={budget['used']/1e6:.0f}MB")


if __name__ == "__main__":
    main()
