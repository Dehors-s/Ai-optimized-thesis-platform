"""为已有的自动化学报摘要回填 PDF 与全文。

用法：py tools/backfill_pdfs.py --limit 120 --max-mb 250
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import pymupdf
import requests

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
MANIFEST = CORPUS / "manifest.jsonl"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
PDF_TPL = "https://www.aas.net.cn/cn/article/pdf/preview/{doi}.pdf"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=120)
    ap.add_argument("--max-mb", type=int, default=250)
    ap.add_argument("--delay", type=float, default=0.3)
    args = ap.parse_args()

    rows = [json.loads(l) for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]
    todo = [r for r in rows if r.get("journal") == "自动化学报" and r.get("doi") and not r.get("pdf_bytes")]
    todo = todo[: args.limit]
    print(f"rows={len(rows)} todo={len(todo)}", flush=True)

    s = requests.Session()
    s.trust_env = False
    s.headers.update({"User-Agent": UA, "Referer": "https://www.aas.net.cn/"})
    used = 0
    done = 0

    for r in todo:
        if used > args.max_mb * 1024 * 1024:
            break
        doi = r["doi"]
        safe = re.sub(r"[^0-9A-Za-z._-]+", "_", doi)
        out = CORPUS / "pdf" / "aas" / f"{safe}.pdf"
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            if not out.exists():
                resp = s.get(PDF_TPL.format(doi=doi), timeout=90)
                if resp.status_code != 200 or not resp.content.startswith(b"%PDF"):
                    continue
                if len(resp.content) < 30_000:
                    continue
                out.write_bytes(resp.content)
                used += len(resp.content)
            size = out.stat().st_size
            r["pdf_bytes"] = size
            doc = pymupdf.open(out)
            text = "\n".join(p.get_text() for p in doc)
            r["pdf_pages"] = doc.page_count
            r["text_chars"] = len(text)
            tp = CORPUS / "text" / "aas" / f"{safe}.txt"
            tp.parent.mkdir(parents=True, exist_ok=True)
            tp.write_text(text, encoding="utf-8")
            done += 1
            if done % 10 == 0:
                print(f"done={done} used={used/1e6:.0f}MB", flush=True)
                MANIFEST.write_text(
                    "\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n",
                    encoding="utf-8",
                )
        except Exception as e:
            print("ERR", doi, type(e).__name__, flush=True)
        time.sleep(args.delay)

    MANIFEST.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n",
        encoding="utf-8",
    )
    print(f"finish done={done} used={used/1e6:.0f}MB", flush=True)


if __name__ == "__main__":
    main()
