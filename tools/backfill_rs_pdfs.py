"""回填《测绘学报》PDF 全文，并校验正文质量（下载并发、抽取串行）。

用法：py tools/backfill_rs_pdfs.py --limit 200 --max-mb 1000 --workers 6
"""

from __future__ import annotations

import argparse
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pymupdf
import requests

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
MANIFEST = CORPUS / "manifest.jsonl"
REPORT = CORPUS / "rs_pdf_report.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
PDF_TPL = "http://xb.chinasmp.com/CN/article/downloadArticleFile.do?attachType=PDF&id={id}"

_tls = threading.local()


def sess() -> requests.Session:
    if not hasattr(_tls, "s"):
        s = requests.Session()
        s.trust_env = False
        s.headers.update({"User-Agent": UA, "Referer": "http://xb.chinasmp.com/"})
        _tls.s = s
    return _tls.s


def abstract_id(url: str) -> str | None:
    m = re.search(r"abstract(\d+)\.shtml", url)
    return m.group(1) if m else None


def check(doc: pymupdf.Document, text: str, empty_pages: int) -> dict:
    zh = len(re.findall(r"[\u4e00-\u9fff]", text))
    pages = doc.page_count
    bad = text.count("\ufffd")
    refs = ("参考文献" in text) or ("References" in text)
    ok = (
        pages >= 4
        and len(text) >= 6000
        and zh >= 2000
        and refs
        and bad / max(len(text), 1) < 0.005
        and empty_pages <= max(1, pages // 5)
    )
    return {
        "pdf_pages": pages,
        "text_chars": len(text),
        "text_zh": zh,
        "chars_per_page": round(len(text) / max(pages, 1), 1),
        "empty_pages": empty_pages,
        "has_refs": refs,
        "replacement_ratio": round(bad / max(len(text), 1), 5),
        "text_ok": ok,
    }


def download(row: dict, max_pdf_mb: int = 12, reconcile: bool = False) -> tuple[dict, Path | None, int, str]:
    aid = abstract_id(row["url"])
    out = CORPUS / "pdf" / "xb" / f"{aid}.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_size > 100_000:
        return row, out, out.stat().st_size, ""
    if reconcile:
        return row, None, 0, "missing"
    url = PDF_TPL.format(id=aid)
    try:
        head = sess().head(url, timeout=30, allow_redirects=True)
        cl = int(head.headers.get("Content-Length") or 0)
        if cl > max_pdf_mb * 1024 * 1024:
            return row, None, 0, f"too large {cl/1e6:.1f}MB"
    except Exception:
        pass
    try:
        resp = sess().get(url, timeout=120)
        if resp.status_code != 200 or not resp.content.startswith(b"%PDF"):
            return row, None, 0, f"bad status {resp.status_code}"
        if len(resp.content) < 100_000:
            return row, None, 0, "too small"
        out.write_bytes(resp.content)
        return row, out, len(resp.content), ""
    except Exception as e:
        return row, None, 0, type(e).__name__


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--max-mb", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--max-pdf-mb", type=int, default=12)
    ap.add_argument("--reconcile", action="store_true")
    ap.add_argument("--year-from", default="")
    args = ap.parse_args()

    rows = [json.loads(l) for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]
    todo = [
        r for r in rows
        if r.get("journal") == "测绘学报" and abstract_id(r.get("url", "")) and not r.get("pdf_bytes")
    ]
    if args.year_from:
        todo = [r for r in todo if str(r.get("year", "")) >= args.year_from]
    print(f"rows={len(rows)} candidates={len(todo)}", flush=True)

    used = 0
    good = 0
    tried = 0
    qc_rows = []
    ex = ThreadPoolExecutor(max_workers=args.workers)
    futs = [ex.submit(download, r, args.max_pdf_mb, args.reconcile) for r in todo]

    try:
        for fut in as_completed(futs):
            row, path, size, err = fut.result()
            tried += 1
            if not path:
                continue
            used += size
            try:
                doc = pymupdf.open(path)
                page_texts = [p.get_text() for p in doc]
                text = "\n".join(page_texts)
                empty = sum(1 for t in page_texts if len(t.strip()) < 50)
                qc = check(doc, text, empty)
                qc["pdf_bytes"] = size
                qc_rows.append({"id": abstract_id(row["url"]), "title": row.get("title", ""), **qc})
                row.update(qc)
                if qc["text_ok"]:
                    tp = CORPUS / "text" / "xb" / f"{abstract_id(row['url'])}.txt"
                    tp.parent.mkdir(parents=True, exist_ok=True)
                    tp.write_text(text, encoding="utf-8")
                    good += 1
            except Exception as e:
                row["text_ok"] = False
                row["qc_error"] = type(e).__name__
            if tried % 20 == 0:
                print(f"tried={tried} good={good} used={used/1e6:.0f}MB", flush=True)
            if good >= args.limit or used > args.max_mb * 1024 * 1024:
                break
    finally:
        ex.shutdown(wait=False, cancel_futures=True)
        MANIFEST.write_text(
            "\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n",
            encoding="utf-8",
        )

    ok_rows = [q for q in qc_rows if q["text_ok"]]
    summary = {
        "target": args.limit,
        "good": good,
        "tried": tried,
        "used_mb": round(used / 1e6, 1),
        "pages": {
            "min": min((q["pdf_pages"] for q in ok_rows), default=0),
            "median": sorted(q["pdf_pages"] for q in ok_rows)[len(ok_rows) // 2] if ok_rows else 0,
            "max": max((q["pdf_pages"] for q in ok_rows), default=0),
        },
        "chars": {
            "min": min((q["text_chars"] for q in ok_rows), default=0),
            "median": sorted(q["text_chars"] for q in ok_rows)[len(ok_rows) // 2] if ok_rows else 0,
            "max": max((q["text_chars"] for q in ok_rows), default=0),
        },
        "empty_pages_total": sum(q["empty_pages"] for q in ok_rows),
        "failed": [q for q in qc_rows if not q["text_ok"]][:20],
    }
    REPORT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"finish good={good} tried={tried} used={used/1e6:.0f}MB", flush=True)


if __name__ == "__main__":
    main()
