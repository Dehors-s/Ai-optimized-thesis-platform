"""校验《测绘学报》全文文本：页数、空页、字符、参考文献、抽样结构。

用法：py tools/audit_rs_texts.py
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
MANIFEST = CORPUS / "manifest.jsonl"
OUT = CORPUS / "rs_text_audit.json"


def main() -> None:
    rows = [json.loads(l) for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]
    rs = [r for r in rows if r.get("journal") == "测绘学报" and r.get("text_ok")]
    print("good rows", len(rs))

    missing, bad_len, no_refs, low_zh = [], [], [], []
    samples = []
    for r in rs:
        aid = r["id"] if r.get("id") else ""
        # id 是 url 哈希，PDF 文件名是摘要 id，这里从 url 推
        m = re.search(r"abstract(\d+)\.shtml", r.get("url", ""))
        key = m.group(1) if m else aid
        tp = CORPUS / "text" / "xb" / f"{key}.txt"
        if not tp.exists():
            missing.append(key)
            continue
        t = tp.read_text(encoding="utf-8", errors="ignore")
        if abs(len(t) - r.get("text_chars", 0)) > 50:
            bad_len.append((key, len(t), r.get("text_chars")))
        if "参考文献" not in t and "References" not in t:
            no_refs.append(key)
        zh = len(re.findall(r"[\u4e00-\u9fff]", t))
        if zh < 2000:
            low_zh.append((key, zh))
        if len(samples) < 5:
            heads = re.findall(r"(?m)^\s*([0-9]{1,2})\s+([\u4e00-\u9fff]{2,12})", t)[:8]
            samples.append({
                "id": key,
                "chars": len(t),
                "head": re.sub(r"\s+", " ", t[:160]),
                "sections": [f"{a} {b}" for a, b in heads],
            })

    # 抽 8 篇重开 PDF，核对页数与空页
    check = []
    rng = random.Random(7)
    for r in rng.sample(rs, min(8, len(rs))):
        m = re.search(r"abstract(\d+)\.shtml", r.get("url", ""))
        key = m.group(1) if m else ""
        pdf = CORPUS / "pdf" / "xb" / f"{key}.pdf"
        if not pdf.exists():
            continue
        doc = pymupdf.open(pdf)
        empty = sum(1 for p in doc if len(p.get_text().strip()) < 50)
        check.append({"id": key, "pages": doc.page_count, "empty_pages": empty,
                      "first_page_chars": len(doc[0].get_text())})

    summary = {
        "good_texts": len(rs),
        "missing_files": len(missing),
        "length_mismatch": len(bad_len),
        "no_references": len(no_refs),
        "low_chinese": len(low_zh),
        "sampled_pdfs": check,
        "samples": samples,
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("samples", "sampled_pdfs")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
