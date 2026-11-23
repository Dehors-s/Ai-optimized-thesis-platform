"""抓取神经网络/方法架构图：Nature 系列 + 顶会论文（arXiv 版）。

用法：
  py tools/crawl_arch.py --nature PMC13714282 PMC13346949 PMC13212600 PMC13438114
  py tools/crawl_arch.py --arxiv 1512.03385 1505.04597 1706.03762 2010.11929 2103.14030 2304.02643

产物：
  corpus/figures/arch/{nature,arxiv}/*.png
  corpus/figures/arch/manifest.jsonl

只抓 OA（Nature Communications 的 CC BY 文章）与 arXiv 公开页面。
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "corpus" / "figures" / "arch"
MANIFEST = OUT / "manifest.jsonl"
UA = {"User-Agent": "Mozilla/5.0 paperkit-archstudy/1.0"}
PAT = re.compile(r"architect|framework|overview|schematic|pipeline|workflow|"
                 r"network structure|model structure|method overview", re.I)


def get(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def strip(s: str) -> str:
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def save(url: str, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    p = subprocess.run(["curl.exe", "-L", "--max-time", "60", "-s",
                        "-A", UA["User-Agent"], "-o", str(tmp), url], capture_output=True)
    if p.returncode != 0 or not tmp.exists() or tmp.stat().st_size < 4000:
        tmp.unlink(missing_ok=True)
        raise ValueError("download failed")
    tmp.replace(path)
    return path.stat().st_size


def append(rec: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def nature(pmcid: str) -> int:
    xml = get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML")
    doi = (re.search(r'<article-id pub-id-type="doi">([^<]+)</article-id>', xml) or [None, ""])[1]
    title = strip((re.search(r"(?s)<article-title>(.*?)</article-title>", xml) or [None, ""])[1])
    n = 0
    for k, block in enumerate(re.findall(r"(?s)<fig\b[^>]*>.*?</fig>", xml)[:3], 1):
        cap = strip((re.search(r"(?s)<caption>(.*?)</caption>", block) or [None, ""])[1])
        if not cap or not PAT.search(cap):
            continue
        g = re.search(r'<graphic[^>]*xlink:href="([^"]+)"', block)
        if not g:
            continue
        lab = strip((re.search(r"(?s)<label>(.*?)</label>", block) or [None, ""])[1])
        href = re.sub(r"\.(jpg|jpeg|gif|webp|tif|tiff)$", "", g.group(1))
        base = ("https://media.springernature.com/full/springer-static/image/art%3A"
                + urllib.parse.quote(doi, safe="") + "/MediaObjects/" + href)
        path = OUT / "nature" / f"{pmcid}-f{k}.png"
        size = None
        for ext in (".png", ".jpg"):
            try:
                size = save(base + ext, path)
                break
            except Exception:  # noqa: BLE001
                continue
        if not size:
            continue
        num = re.sub(r"\D", "", lab) or str(k)
        cite = ""
        for p in re.findall(r"(?s)<p\b[^>]*>.*?</p>", xml):
            t = strip(p)
            if re.search(rf"\b(Fig\.?|Figure)\s*{num}\b", t, re.I):
                cite = t
                break
        append({"source": "nature", "venue": "Nature Communications", "pmcid": pmcid,
                "doi": doi, "title": title, "fig": lab, "file": str(path.relative_to(ROOT)),
                "caption": cap, "cite": cite[:400], "bytes": size})
        n += 1
        break  # 每篇只取第一张架构图
    return n


def arxiv(aid: str, venue: str = "") -> int:
    page, base = "", ""
    for u in (f"https://ar5iv.labs.arxiv.org/html/{aid}", f"https://arxiv.org/html/{aid}"):
        try:
            page = get(u)
            base = u
            break
        except Exception:  # noqa: BLE001
            continue
    if not page:
        print("  arxiv fail", aid)
        return 0
    title = strip((re.search(r"(?is)<h1[^>]*class=\"ltx_title[^\"]*\"[^>]*>(.*?)</h1>", page)
                   or re.search(r"(?is)<title>(.*?)</title>", page) or [None, ""])[1])
    for k, block in enumerate(re.findall(r"(?is)<figure\b.*?</figure>", page), 1):
        cap = strip((re.search(r"(?is)<figcaption[^>]*>(.*?)</figcaption>", block) or [None, ""])[1])
        if not cap or not PAT.search(cap):
            continue
        img = re.search(r'<img[^>]+src="([^"]+)"', block)
        if not img:
            continue
        src = urllib.parse.urljoin(base, img.group(1))
        path = OUT / "arxiv" / f"{aid}-f{k}.png"
        try:
            size = save(src, path)
        except Exception as e:  # noqa: BLE001
            print("  img fail", src, e)
            continue
        append({"source": "arxiv", "venue": venue or "arXiv", "arxiv": aid, "title": title,
                "fig": f"Fig.{k}", "file": str(path.relative_to(ROOT)),
                "caption": cap, "cite": "", "bytes": size})
        return 1
    return 0


CLASSIC = {
    "1512.03385": "CVPR 2016 (ResNet)",
    "1505.04597": "MICCAI 2015 (U-Net)",
    "1706.03762": "NeurIPS 2017 (Transformer)",
    "2010.11929": "ICLR 2021 (ViT)",
    "2103.14030": "ICCV 2021 (Swin)",
    "2304.02643": "ICCV 2023 (SAM)",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nature", nargs="*", default=[])
    ap.add_argument("--arxiv", nargs="*", default=[])
    args = ap.parse_args()

    total = 0
    for p in args.nature:
        print("nature", p)
        total += nature(p)
    for a in args.arxiv:
        print("arxiv", a)
        total += arxiv(a, CLASSIC.get(a, ""))
    print("saved", total)


if __name__ == "__main__":
    main()
