"""抓取开放获取论文的图表，建成可统计的图表语料库。

用法：
  py tools/crawl_figures.py --journal gmd --articles 10
  py tools/crawl_figures.py --journal essd --articles 8
  py tools/crawl_figures.py --journal natcomms --articles 8
  py tools/crawl_figures.py --journal all --articles 8

产物：
  corpus/figures/corpus/{journal}/{article}-f{n}.{ext}
  corpus/figures/corpus/manifest.jsonl

只抓 OA 源：Copernicus（CC BY）与 Europe PMC 索引的 Nature Communications（CC BY）。
不碰付费墙，不绕反爬；失败就跳过并记录。
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("FIGCORPUS_OUT", ROOT / "corpus" / "figures" / "corpus"))
if not OUT.is_absolute():
    OUT = ROOT / OUT
MANIFEST = OUT / "manifest.jsonl"
UA = {"User-Agent": "Mozilla/5.0 paperkit-figcorpus/1.0"}

COP = {
    "gmd": ("Geoscientific Model Development", "gmd"),
    "essd": ("Earth System Science Data", "essd"),
    "nhess": ("Natural Hazards and Earth System Sciences", "nhess"),
    "tc": ("The Cryosphere", "tc"),
    "bg": ("Biogeosciences", "bg"),
    "acp": ("Atmospheric Chemistry and Physics", "acp"),
    "amt": ("Atmospheric Measurement Techniques", "amt"),
    "cp": ("Climate of the Past", "cp"),
    "hess": ("Hydrology and Earth System Sciences", "hess"),
    "ocean": ("Ocean Science", "os"),
    "se": ("Solid Earth", "se"),
    "wcd": ("Weather and Climate Dynamics", "wcd"),
}


def http_text(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def curl_text(url: str, timeout: int = 60) -> str:
    p = subprocess.run(["curl.exe", "-L", "--max-time", str(timeout), "-s", url],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return p.stdout or ""


def save(url: str, path: Path) -> int:
    """用 curl 下载，避免 urllib 在部分 CDN 上挂起。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    p = subprocess.run(["curl.exe", "-L", "--max-time", "60", "-s",
                        "-A", UA["User-Agent"], "-o", str(tmp), url],
                       capture_output=True)
    if p.returncode != 0 or not tmp.exists() or tmp.stat().st_size < 5000:
        tmp.unlink(missing_ok=True)
        raise ValueError("download failed or too small")
    tmp.replace(path)
    return path.stat().st_size


def strip(s: str) -> str:
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def crossref(container: str, rows: int) -> list[dict]:
    q = urllib.parse.quote(f"container-title:{container},from-pub-date:2025-01-01,type:journal-article")
    url = f"https://api.crossref.org/works?filter={q}&rows={rows}&select=DOI,title,published"
    data = json.loads(http_text(url))
    return data["message"]["items"]


def append(rec: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def crawl_copernicus(key: str, rows: int) -> int:
    name, code = COP[key]
    n = 0
    for item in crossref(name, rows):
        doi = item["DOI"]
        m = re.match(rf"10\.5194/{code}-(\d+)-(\d+)-(\d+)", doi)
        if not m:
            continue
        vol, page, year = m.groups()
        url = f"https://{code}.copernicus.org/articles/{vol}/{page}/{year}/"
        page_html = curl_text(url)
        if "class=\"fig\"" not in page_html:
            print("  skip", doi)
            continue
        blocks = re.split(r'(?is)<div class="fig"', page_html)[1:]
        for k, block in enumerate(blocks, 1):
            img = re.search(r'data-webversion="([^"]+)"', block) or re.search(r'href="([^"]+\.png)"', block)
            cap = strip((re.search(r'(?is)<div class="caption">(.*?)</div>', block) or [None, ""])[1])
            if not img or not cap:
                continue
            src = img.group(1)
            ext = ".png"
            path = OUT / key / f"{doi.replace('/', '_')}-f{k:02d}{ext}"
            rec = {"source": "copernicus", "journal": key, "doi": doi, "url": url,
                   "fig": k, "file": str(path.relative_to(ROOT)), "caption": cap}
            if path.exists() and path.stat().st_size > 5000:
                rec["bytes"] = path.stat().st_size
                append(rec)  # 断点续抓：已有文件也补登 manifest
                continue
            try:
                size = save(src, path)
            except Exception as e:  # noqa: BLE001
                print("  img fail", src, e, flush=True)
                continue
            rec["bytes"] = size
            append(rec)
            n += 1
        time.sleep(0.4)
    return n


def crawl_natcomms(rows: int) -> int:
    n = 0
    for item in crossref("Nature Communications", rows):
        doi = item["DOI"]
        try:
            q = urllib.parse.quote(f"DOI:{doi}")
            j = json.loads(http_text(
                f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={q}&format=json&resultType=lite"))
            res = j.get("resultList", {}).get("result", [])
            if not res or not res[0].get("pmcid"):
                continue
            pmcid = res[0]["pmcid"]
            xml = http_text(f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML")
        except Exception as e:  # noqa: BLE001
            print("  skip", doi, e)
            continue
        for k, block in enumerate(re.findall(r"(?s)<fig\b[^>]*>.*?</fig>", xml)[:4], 1):
            cap = strip((re.search(r"(?s)<caption>(.*?)</caption>", block) or [None, ""])[1])
            g = re.search(r'<graphic[^>]*xlink:href="([^"]+)"', block)
            if not cap or not g:
                continue
            href = re.sub(r"\.(jpg|jpeg|gif|webp|tif|tiff)$", "", g.group(1))
            base = ("https://media.springernature.com/full/springer-static/image/art%3A"
                    + urllib.parse.quote(doi, safe="") + "/MediaObjects/" + href)
            path = OUT / "natcomms" / f"{doi.replace('/', '_')}-f{k:02d}.png"
            size = None
            for ext in (".png", ".jpg"):
                try:
                    size = save(base + ext, path)
                    break
                except Exception:  # noqa: BLE001
                    continue
            if not size:
                continue
            append({"source": "nature", "journal": "natcomms", "doi": doi,
                    "url": f"https://doi.org/{doi}", "fig": k,
                    "file": str(path.relative_to(ROOT)), "caption": cap, "bytes": size})
            n += 1
        time.sleep(0.5)
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", default="all", choices=["all", *COP, "natcomms"])
    ap.add_argument("--articles", type=int, default=8)
    args = ap.parse_args()

    targets = list(COP) + ["natcomms"] if args.journal == "all" else [args.journal]
    total = 0
    for t in targets:
        print("==", t)
        total += crawl_natcomms(args.articles) if t == "natcomms" else crawl_copernicus(t, args.articles)
    print(f"total figures: {total}")


if __name__ == "__main__":
    main()
