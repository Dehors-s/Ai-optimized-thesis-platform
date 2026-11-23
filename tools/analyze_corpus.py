"""分析语料库的语体特征，产出 style_profile.json 与 style_report.md。

用法：py tools/analyze_corpus.py
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
TEXT_DIR = CORPUS / "text"
OUT_JSON = CORPUS / "style_profile.json"
OUT_MD = CORPUS / "style_report.md"

PUNCT = ["，", "。", "；", "：", "、", "——", "（", "）", "“", "”"]
CONNECTIVES = [
    "首先", "然后", "其次", "最后", "此外", "然而", "因此", "从而", "进而",
    "在此基础上", "针对", "为此", "同时", "但是", "并且", "通过", "采用",
    "提出", "构建", "实现", "表明", "验证",
]


def zh_ratio(t: str) -> float:
    if not t:
        return 0.0
    return len(re.findall(r"[\u4e00-\u9fff]", t)) / len(t)


def normalize(t: str) -> str:
    """部分期刊 HTML 把中文句读转成了半角 \". \" / \", \"，这里统一回中文标点。"""
    t = re.sub(r"(?<=[^\d])\.\s+", "。", t)
    t = re.sub(r",\s+", "，", t)
    t = re.sub(r";\s+", "；", t)
    t = re.sub(r":\s+", "：", t)
    return t


def split_sents(t: str) -> list[str]:
    t = normalize(t)
    parts = re.split(r"(?<=[。！？])", t)
    return [p.strip() for p in parts if len(p.strip()) >= 8 and zh_ratio(p) > 0.4]


def pct(xs: list[float], q: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def summarize(sents: list[str], abstracts: list[str]) -> dict:
    lens = [len(s) for s in sents]
    commas = [s.count("，") + s.count(",") for s in sents]
    de = [s.count("的") for s in sents]
    total_chars = sum(len(a) for a in abstracts) or 1
    d = {
        "n_abstracts": len(abstracts),
        "n_sentences": len(sents),
        "abstract_len": {
            "mean": round(statistics.mean([len(a) for a in abstracts]), 1) if abstracts else 0,
            "median": statistics.median([len(a) for a in abstracts]) if abstracts else 0,
            "p10": round(pct([len(a) for a in abstracts], 0.10), 1),
            "p90": round(pct([len(a) for a in abstracts], 0.90), 1),
        },
        "sent_len": {
            "mean": round(statistics.mean(lens), 1) if lens else 0,
            "median": statistics.median(lens) if lens else 0,
            "p90": round(pct(lens, 0.90), 1),
            "max": max(lens) if lens else 0,
            "share_gt60": round(sum(1 for x in lens if x > 60) / len(lens), 3) if lens else 0,
            "share_gt80": round(sum(1 for x in lens if x > 80) / len(lens), 3) if lens else 0,
            "share_gt100": round(sum(1 for x in lens if x > 100) / len(lens), 3) if lens else 0,
        },
        "commas_per_sent": round(statistics.mean(commas), 2) if commas else 0,
        "de_per_sent": round(statistics.mean(de), 2) if de else 0,
        "share_sent_ge2de": round(sum(1 for x in de if x >= 2) / len(de), 3) if de else 0,
        "punct_per_1000": {
            p: round(sum(a.count(p) for a in abstracts) * 1000 / total_chars, 2) for p in PUNCT
        },
        "connectives_per_10k": {
            c: round(sum(a.count(c) for a in abstracts) * 10000 / total_chars, 1) for c in CONNECTIVES
        },
    }
    return d


def main() -> None:
    rows = [json.loads(l) for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if len(r.get("abstract", "")) >= 80]
    for r in rows:
        r["abstract"] = normalize(r["abstract"])
    abstracts = [r["abstract"] for r in rows]
    sents: list[str] = []
    for a in abstracts:
        sents += split_sents(a)

    texts = []
    for p in TEXT_DIR.glob("**/*.txt"):
        t = p.read_text(encoding="utf-8", errors="ignore")
        # 去掉参考文献之后的内容，降低噪声
        cut = t.find("参考文献")
        if cut > 0:
            t = t[:cut]
        texts.append(t)
    tsents: list[str] = []
    for t in texts:
        tsents += split_sents(t)

    st = summarize(sents, abstracts)
    st_text = summarize(tsents, texts) if texts else None

    # 开头 / 结尾
    st["openings"] = Counter([a[:8] for a in abstracts]).most_common(15)
    st["endings"] = Counter([a[-8:] for a in abstracts]).most_common(15)

    # 长句样例（带 2 个以上“的”）
    long_examples = sorted(
        [s for s in sents if s.count("的") >= 2], key=len, reverse=True
    )[:12]
    st["long_sentence_examples"] = long_examples

    journals = Counter([r.get("journal", "?") for r in rows])
    years = Counter([str(r.get("year", ""))[:4] for r in rows])
    st["journals"] = journals.most_common()
    st["years"] = sorted(years.items())
    st["pdf_count"] = sum(1 for r in rows if r.get("pdf_bytes"))
    st["pdf_mb"] = round(sum(r.get("pdf_bytes", 0) for r in rows) / 1e6, 1)
    st["text_chars"] = sum(r.get("text_chars", 0) for r in rows)

    OUT_JSON.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")

    def p(k, v):
        return f"| {k} | {v} |"

    lines = [
        "# 语料语体分析报告",
        "",
        f"- 摘要数：{st['n_abstracts']}；句子数：{st['n_sentences']}",
        f"- 期刊：{', '.join(f'{k} {v}' for k, v in st['journals'])}",
        f"- 年份：{st['years'][0][0]}–{st['years'][-1][0]}" if st["years"] else "",
        f"- PDF：{st['pdf_count']} 篇，{st['pdf_mb']} MB；全文 {st['text_chars']:,} 字符",
        "",
        "## 摘要",
        "| 指标 | 值 |",
        "|---|---|",
        p("平均字数", st["abstract_len"]["mean"]),
        p("中位字数", st["abstract_len"]["median"]),
        p("P10 / P90", f"{st['abstract_len']['p10']} / {st['abstract_len']['p90']}"),
        "",
        "## 句子",
        "| 指标 | 值 |",
        "|---|---|",
        p("平均句长", st["sent_len"]["mean"]),
        p("中位句长", st["sent_len"]["median"]),
        p("P90 / 最长", f"{st['sent_len']['p90']} / {st['sent_len']['max']}"),
        p(">60 字比例", st["sent_len"]["share_gt60"]),
        p(">80 字比例", st["sent_len"]["share_gt80"]),
        p(">100 字比例", st["sent_len"]["share_gt100"]),
        p("每句逗号数", st["commas_per_sent"]),
        "",
        "## “的”与长定语",
        "| 指标 | 值 |",
        "|---|---|",
        p("每句“的”数", st["de_per_sent"]),
        p("含 ≥2 个“的”的句子比例", st["share_sent_ge2de"]),
        "",
        "## 标点（每千字）",
        "| 标点 | 频次 |",
        "|---|---|",
    ] + [p(k, v) for k, v in st["punct_per_1000"].items()] + [
        "",
        "## 连接词（每万字）",
        "| 词 | 频次 |",
        "|---|---|",
    ] + [p(k, v) for k, v in st["connectives_per_10k"].items()] + [
        "",
        "## 开头 / 结尾",
        "开头 Top：" + "；".join(f"{k}（{v}）" for k, v in st["openings"][:8]),
        "",
        "结尾 Top：" + "；".join(f"{k}（{v}）" for k, v in st["endings"][:8]),
        "",
        "## 长句样例（可模仿的长定语结构）",
    ]
    for s in long_examples:
        lines.append(f"- （{len(s)} 字）{s}")

    if st_text:
        lines += [
            "",
            "## 全文（PDF）对照",
            "| 指标 | 摘要 | 全文 |",
            "|---|---|---|",
            f"| 平均句长 | {st['sent_len']['mean']} | {st_text['sent_len']['mean']} |",
            f"| 中位句长 | {st['sent_len']['median']} | {st_text['sent_len']['median']} |",
            f"| >80 字比例 | {st['sent_len']['share_gt80']} | {st_text['sent_len']['share_gt80']} |",
            f"| 每句逗号数 | {st['commas_per_sent']} | {st_text['commas_per_sent']} |",
            f"| 每句“的”数 | {st['de_per_sent']} | {st_text['de_per_sent']} |",
        ]

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print("written", OUT_JSON.name, OUT_MD.name, "n=", st["n_abstracts"])


if __name__ == "__main__":
    main()
