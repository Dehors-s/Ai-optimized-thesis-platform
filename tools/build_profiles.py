"""从语料库生成可执行的「语体画像」（style profile）。

用法：py tools/build_profiles.py
输出：corpus/profiles/rs_abstract.json、cs_abstract.json、rs_body.json
"""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
OUT = CORPUS / "profiles"
MANIFEST = CORPUS / "manifest.jsonl"


def normalize(t: str) -> str:
    t = re.sub(r"(?<=[^\d])\.\s+", "。", t)
    t = re.sub(r",\s+", "，", t)
    return t


def clean_full(t: str) -> str:
    i = t.find("参考文献")
    if i > 2000:
        t = t[:i]
    t = t.replace("\n", "")
    t = re.sub(r"(?<!\d)\.(?!\d)", "。", t)
    t = t.replace(",", "，").replace(";", "；").replace(":", "：")
    return t


def zh_ratio(t: str) -> float:
    return len(re.findall(r"[\u4e00-\u9fff]", t)) / max(len(t), 1)


def sents(t: str, lo: int = 8, hi: int = 300, min_zh: float = 0.35) -> list[str]:
    out = []
    for s in re.split(r"(?<=[。！？])", normalize(t)):
        s = s.strip()
        if lo <= len(s) <= hi and zh_ratio(s) > min_zh:
            out.append(s)
    return out


def pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    if not xs:
        return 0
    k = (len(xs) - 1) * q
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def profile(docs: list[str], ss: list[str], pid: str, domain: str, genre: str) -> dict:
    lens = [len(s) for s in ss]
    zh = sum(len(re.findall(r"[\u4e00-\u9fff]", d)) for d in docs) or 1
    total = sum(len(d) for d in docs) or 1
    de = sum(s.count("的") for s in ss)
    comma = sum(s.count("，") for s in ss)
    return {
        "id": pid,
        "domain": domain,
        "genre": genre,
        "n_docs": len(docs),
        "length": {
            "median": round(statistics.median([len(d) for d in docs]), 1),
            "p10": round(pct([len(d) for d in docs], 0.1), 1),
            "p90": round(pct([len(d) for d in docs], 0.9), 1),
        },
        "sentence": {
            "mean": round(statistics.mean(lens), 1),
            "median": statistics.median(lens),
            "p90": round(pct(lens, 0.9), 1),
            "gt60": round(sum(1 for x in lens if x > 60) / len(lens), 3),
            "gt80": round(sum(1 for x in lens if x > 80) / len(lens), 3),
        },
        "commas_per_sentence": round(comma / len(ss), 2),
        "de_per_100_zh": round(de / zh * 100, 2),
        "semicolon_per_1000": round(sum(d.count("；") for d in docs) * 1000 / total, 2),
        "dash_per_1000": round(sum(d.count("——") for d in docs) * 1000 / total, 2),
        "quote_per_1000": round(sum(d.count("“") for d in docs) * 1000 / total, 2),
        "hard_rules": {
            "max_dash": 0,
            "max_quote": 0,
            "meta_blacklist": ["归因给出", "上述结论", "本文的价值", "值得注意的是", "综上所述", "首先其次最后"],
            "comma_tolerance": 0.4,
            "de_tolerance": 0.6,
        },
        "soft_rules": {
            "sentence_mean_tolerance": 15,
            "gt80_tolerance": 0.2,
        },
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]

    rs = [r for r in rows if r.get("journal") == "测绘学报" and len(r.get("abstract", "")) >= 80]
    cs = [r for r in rows if r.get("journal") == "自动化学报" and len(r.get("abstract", "")) >= 80]
    rs_abs = [normalize(r["abstract"]) for r in rs]
    cs_abs = [normalize(r["abstract"]) for r in cs]

    body = []
    for r in rs:
        if not r.get("text_ok"):
            continue
        m = re.search(r"abstract(\d+)\.shtml", r.get("url", ""))
        p = CORPUS / "text" / "xb" / f"{m.group(1)}.txt" if m else None
        if p and p.exists():
            body.append(clean_full(p.read_text(encoding="utf-8", errors="ignore")))

    for pid, docs, domain, genre, lo, hi, mz in [
        ("rs_abstract", rs_abs, "remote_sensing", "abstract", 8, 300, 0.35),
        ("cs_abstract", cs_abs, "computer_science", "abstract", 8, 300, 0.35),
        ("rs_body", body, "remote_sensing", "body", 15, 300, 0.6),
    ]:
        ss: list[str] = []
        for d in docs:
            ss += sents(d, lo, hi, mz)
        prof = profile(docs, ss, pid, domain, genre)
        (OUT / f"{pid}.json").write_text(json.dumps(prof, ensure_ascii=False, indent=2), encoding="utf-8")
        print(pid, prof["n_docs"], prof["sentence"]["mean"], prof["commas_per_sentence"], prof["de_per_100_zh"])


if __name__ == "__main__":
    main()
