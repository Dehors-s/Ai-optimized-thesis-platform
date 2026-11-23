"""重算遥感侧（《测绘学报》）的句法指标：摘要 vs 全文，并与 v4 摘要对照。

用法：py tools/analyze_rs.py
输出：corpus/rs_style_report.md、corpus/rs_style_profile.json
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
MANIFEST = CORPUS / "manifest.jsonl"
OUT_MD = CORPUS / "rs_style_report.md"
OUT_JSON = CORPUS / "rs_style_profile.json"

PUNCT = ["，", "。", "；", "、", "——", "（", "）", "“", "”"]
CONN = ["首先", "其次", "然后", "最后", "此外", "然而", "因此", "从而", "进而",
        "在此基础上", "针对", "为此", "通过", "采用", "提出", "表明", "验证"]


def normalize(t: str) -> str:
    t = re.sub(r"(?<=[^\d])\.\s+", "。", t)
    t = re.sub(r",\s+", "，", t)
    t = re.sub(r";\s+", "；", t)
    return t


def zh_ratio(t: str) -> float:
    return len(re.findall(r"[\u4e00-\u9fff]", t)) / max(len(t), 1)


def clean_full(t: str) -> str:
    """PDF 全文清洗：去参考文献、并回断行、半角标点归一。"""
    i = t.find("参考文献")
    if i > 2000:
        t = t[:i]
    t = t.replace("\n", "")
    t = re.sub(r"(?<!\d)\.(?!\d)", "。", t)
    t = t.replace(",", "，").replace(";", "；").replace(":", "：")
    return t


def sents(t: str, lo: int = 8, hi: int = 300, min_zh: float = 0.35) -> list[str]:
    t = normalize(t)
    out = []
    for s in re.split(r"(?<=[。！？])", t):
        s = s.strip()
        if lo <= len(s) <= hi and zh_ratio(s) > min_zh:
            out.append(s)
    return out


def pct(xs: list[float], q: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def stat(ss: list[str], docs: list[str]) -> dict:
    lens = [len(s) for s in ss]
    de = [s.count("的") for s in ss]
    commas = [s.count("，") for s in ss]
    total = sum(len(d) for d in docs) or 1
    zh_total = sum(len(re.findall(r"[\u4e00-\u9fff]", d)) for d in docs) or 1
    return {
        "n_docs": len(docs),
        "n_sents": len(ss),
        "chars": sum(len(d) for d in docs),
        "zh_chars": zh_total,
        "zh_ratio": round(zh_total / total, 3),
        "sent_mean": round(statistics.mean(lens), 1) if lens else 0,
        "sent_median": statistics.median(lens) if lens else 0,
        "sent_p90": round(pct(lens, 0.9), 1),
        "sent_max": max(lens) if lens else 0,
        "gt60": round(sum(1 for x in lens if x > 60) / len(lens), 3) if lens else 0,
        "gt80": round(sum(1 for x in lens if x > 80) / len(lens), 3) if lens else 0,
        "gt100": round(sum(1 for x in lens if x > 100) / len(lens), 3) if lens else 0,
        "commas_per_sent": round(statistics.mean(commas), 2) if commas else 0,
        "commas_per_100": round(sum(commas) * 100 / total, 2),
        "commas_per_100_zh": round(sum(commas) * 100 / zh_total, 2),
        "de_per_sent": round(statistics.mean(de), 2) if de else 0,
        "de_per_100": round(sum(de) * 100 / total, 2),
        "de_per_100_zh": round(sum(de) * 100 / zh_total, 2),
        "ge2de": round(sum(1 for x in de if x >= 2) / len(de), 3) if de else 0,
        "ge3de": round(sum(1 for x in de if x >= 3) / len(de), 3) if de else 0,
        "punct_per_1000": {p: round(sum(d.count(p) for d in docs) * 1000 / total, 2) for p in PUNCT},
        "conn_per_10k": {c: round(sum(d.count(c) for d in docs) * 10000 / total, 1) for c in CONN},
    }


def main() -> None:
    rows = [json.loads(l) for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]
    rs = [r for r in rows if r.get("journal") == "测绘学报"]
    abstracts = [normalize(r["abstract"]) for r in rs if len(r.get("abstract", "")) >= 80]

    texts = []
    for r in rs:
        if not r.get("text_ok"):
            continue
        m = re.search(r"abstract(\d+)\.shtml", r.get("url", ""))
        if not m:
            continue
        p = CORPUS / "text" / "xb" / f"{m.group(1)}.txt"
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        texts.append(clean_full(t))

    a_sents: list[str] = []
    for a in abstracts:
        a_sents += sents(a)
    f_sents: list[str] = []
    for t in texts:
        f_sents += sents(t, lo=15, hi=300, min_zh=0.6)

    cs = [normalize(r["abstract"]) for r in rows
          if r.get("journal") == "自动化学报" and len(r.get("abstract", "")) >= 80]
    cs_sents: list[str] = []
    for a in cs:
        cs_sents += sents(a)

    v4_path = ROOT / "outputs" / "摘要_v4_分段版.md"
    v4 = ""
    if v4_path.exists():
        raw = v4_path.read_text(encoding="utf-8")
        v4 = raw.split("## 指标")[0].replace("# 摘要 v4（分段版）", "").strip()
    v4_sents = sents(v4) if v4 else []

    res = {
        "rs_abstract": stat(a_sents, abstracts),
        "rs_fulltext": stat(f_sents, texts),
        "cs_abstract": stat(cs_sents, cs),
        "v4": stat(v4_sents, [v4]) if v4 else {},
        "rs_long_examples": sorted([s for s in f_sents if s.count("的") >= 3], key=len, reverse=True)[:8],
        "rs_abstract_openings": Counter([a[:6] for a in abstracts]).most_common(8),
        "rs_abstract_endings": Counter([a[-8:] for a in abstracts]).most_common(8),
    }
    OUT_JSON.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    def row(label, k):
        d = res[k]
        return (f"| {label} | {d['n_docs']} | {d['n_sents']} | {d['sent_mean']} | {d['sent_median']} | {d['sent_p90']} | "
                f"{d['gt80']:.0%} | {d['commas_per_sent']} | {d['de_per_sent']} | {d['de_per_100_zh']} |")

    lines = [
        "# 遥感侧句法指标（《测绘学报》）",
        "",
        f"- 摘要：{res['rs_abstract']['n_docs']} 篇；全文：{res['rs_fulltext']['n_docs']} 篇",
        f"- 全文字符：{res['rs_fulltext']['chars']:,}（汉字占比 {res['rs_fulltext']['zh_ratio']:.0%}）",
        "",
        "| 语料 | 篇数 | 句数 | 句均长 | 句长中位 | P90 | >80字 | 逗号/句 | 的/句 | 的/百汉字 |",
        "|---|---|---|---|---|---|---|---|---|---|",
        row("遥感摘要", "rs_abstract"),
        row("遥感全文", "rs_fulltext"),
        row("计算机摘要", "cs_abstract"),
        row("v4 摘要", "v4"),
        "",
        "## 高频开头 / 结尾（遥感摘要）",
        "开头：" + "；".join(f"{k}（{v}）" for k, v in res["rs_abstract_openings"]),
        "",
        "结尾：" + "；".join(f"{k}（{v}）" for k, v in res["rs_abstract_endings"]),
        "",
        "## 遥感全文长句样例（≥3 个“的”）",
    ]
    lines += [f"- （{len(s)} 字）{s}" for s in res["rs_long_examples"]]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({k: {kk: v[kk] for kk in ("n_docs", "sent_mean", "commas_per_sent", "de_per_100", "gt80")}
                      for k, v in res.items() if isinstance(v, dict) and "n_docs" in v}, ensure_ascii=False))


if __name__ == "__main__":
    main()
