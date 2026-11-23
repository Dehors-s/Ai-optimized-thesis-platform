"""生成通用中文画像（无期刊匹配时的兜底）。

用法：py tools/build_generic_profiles.py
输出：corpus/profiles/generic_zh_{abstract,method,results,discussion}.json
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_section_profiles import split_sections, normalize, sents, profile  # noqa: E402

CORPUS = ROOT / "corpus"
OUT = CORPUS / "profiles"
MANIFEST = CORPUS / "manifest.jsonl"
DIRS = {"rs": CORPUS / "text" / "xb", "cs": CORPUS / "text" / "aas"}


def main() -> None:
    rows = [json.loads(l) for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]
    abstracts = [normalize(r["abstract"]) for r in rows if len(r.get("abstract", "")) >= 80]
    abs_sents: list[str] = []
    for a in abstracts:
        abs_sents += sents(a)
    prof = profile(abstracts, abs_sents, "generic_zh_abstract", "generic", "abstract")
    (OUT / "generic_zh_abstract.json").write_text(json.dumps(prof, ensure_ascii=False, indent=2), encoding="utf-8")
    print("generic_zh_abstract", prof["n_docs"], prof["sentence"]["mean"], prof["commas_per_sentence"], prof["de_per_100_zh"])

    buckets: dict[str, list[str]] = {"method": [], "results": [], "discussion": []}
    for d in DIRS.values():
        for p in d.glob("*.txt"):
            try:
                t = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for k, body in split_sections(t).items():
                if k in buckets and len(body) > 300:
                    buckets[k].append(normalize(body))

    for k, docs in buckets.items():
        ss: list[str] = []
        for doc in docs:
            ss += sents(doc)
        if len(ss) < 300:
            print("skip", k, len(docs), len(ss))
            continue
        p = profile(docs, ss, f"generic_zh_{k}", "generic", k)
        (OUT / f"generic_zh_{k}.json").write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"generic_zh_{k}", p["n_docs"], p["sentence"]["mean"], p["commas_per_sentence"], p["de_per_100_zh"])


if __name__ == "__main__":
    main()
