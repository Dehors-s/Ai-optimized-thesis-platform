"""按标题切分全文，生成分节语体画像（遥感/测绘 vs 计算机）。

用法：py tools/build_section_profiles.py
输出：corpus/profiles/{rs,cs}_{intro,method,results,discussion,conclusion}.json
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
OUT = CORPUS / "profiles"
TEXT_DIRS = {"rs": CORPUS / "text" / "xb", "cs": CORPUS / "text" / "aas"}

FW_DIGITS = str.maketrans("０１２３４５６７８９．", "0123456789.")


def normalize_line(l: str) -> str:
    l = l.translate(FW_DIGITS).replace("\u3000", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", l).strip()


HEAD = re.compile(r"^(\d{1,2})(?:\.(\d{1,2}))?\s*([\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9\-—、： ]{1,20})$")


def classify(title: str) -> str | None:
    title = title.replace(" ", "")
    if re.search(r"引言|前言|绪论|概述", title):
        return "intro"
    if re.search(r"相关工作|研究现状|文献综述", title):
        return "related"
    if re.search(r"结论|总结|展望", title):
        return "conclusion"
    if re.search(r"实验|结果|评估|验证|对比|性能", title):
        return "results"
    if re.search(r"讨论|分析|消融|敏感性", title):
        return "discussion"
    if re.search(r"方法|模型|原理|框架|算法|设计|流程|系统", title):
        return "method"
    return None


def split_sections(text: str) -> dict[str, str]:
    lines = text.splitlines()
    heads: list[tuple[int, str, str]] = []  # (line_idx, num, title)
    for i, raw in enumerate(lines):
        l = normalize_line(raw)
        if not l or len(l) > 26:
            continue
        m = HEAD.match(l)
        if not m:
            continue
        title = m.group(3)
        heads.append((i, m.group(1), title))
    # 只保留一级标题（无子编号）作为切分点
    tops = [(i, num, title) for i, num, title in heads if "." not in normalize_line(lines[i])[:4]]
    out: dict[str, str] = {}
    for k, (i, num, title) in enumerate(tops):
        typ = classify(title)
        if not typ or typ in out:
            continue
        j = tops[k + 1][0] if k + 1 < len(tops) else len(lines)
        body = "\n".join(lines[i + 1:j])
        if len(body) > 300:
            out[typ] = body
    return out


def normalize(t: str) -> str:
    i = t.find("参考文献")
    if i > 2000:
        t = t[:i]
    t = t.replace("\n", "")
    t = re.sub(r"(?<!\d)\.(?!\d)", "。", t)
    t = t.replace(",", "，").replace(";", "；").replace(":", "：")
    return t


def zh_ratio(t: str) -> float:
    return len(re.findall(r"[\u4e00-\u9fff]", t)) / max(len(t), 1)


def sents(t: str) -> list[str]:
    t = normalize(t)
    return [s.strip() for s in re.split(r"(?<=[。！？])", t)
            if 10 <= len(s.strip()) <= 300 and zh_ratio(s.strip()) > 0.55]


def pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    if not xs:
        return 0
    k = (len(xs) - 1) * q
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def profile(docs: list[str], ss: list[str], pid: str, domain: str, section: str) -> dict:
    lens = [len(s) for s in ss]
    zh = sum(len(re.findall(r"[\u4e00-\u9fff]", d)) for d in docs) or 1
    total = sum(len(d) for d in docs) or 1
    de = sum(s.count("的") for s in ss)
    comma = sum(s.count("，") for s in ss)
    return {
        "id": pid, "domain": domain, "section": section, "n_docs": len(docs), "n_sents": len(ss),
        "sentence": {
            "mean": round(statistics.mean(lens), 1),
            "median": statistics.median(lens),
            "p90": round(pct(lens, 0.9), 1),
            "gt80": round(sum(1 for x in lens if x > 80) / len(lens), 3),
        },
        "commas_per_sentence": round(comma / len(ss), 2),
        "de_per_100_zh": round(de / zh * 100, 2),
        "semicolon_per_1000": round(sum(d.count("；") for d in docs) * 1000 / total, 2),
        "hard_rules": {"max_dash": 0, "max_quote": 3 if section != "abstract" else 1,
                       "comma_tolerance": 0.45, "de_tolerance": 0.7,
                       "meta_blacklist": ["归因给出", "上述结论", "本文的价值", "值得注意的是", "综上所述"]},
        "soft_rules": {"sentence_mean_tolerance": 15, "gt80_tolerance": 0.2},
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    counts: Counter = Counter()
    for domain, d in TEXT_DIRS.items():
        buckets: dict[str, list[str]] = defaultdict(list)
        for p in d.glob("*.txt"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for typ, body in split_sections(text).items():
                buckets[typ].append(body)
        for typ, docs in buckets.items():
            ss: list[str] = []
            for doc in docs:
                ss += sents(doc)
            if len(ss) < 200:
                print("skip", domain, typ, len(docs), len(ss))
                continue
            prof = profile(docs, ss, f"{domain}_{typ}", domain, typ)
            (OUT / f"{domain}_{typ}.json").write_text(json.dumps(prof, ensure_ascii=False, indent=2), encoding="utf-8")
            counts[f"{domain}_{typ}"] = len(docs)
            print(f"{domain}_{typ}: docs={len(docs)} sents={len(ss)} mean={prof['sentence']['mean']} "
                  f"commas={prof['commas_per_sentence']} de={prof['de_per_100_zh']}")
    print(dict(counts))


if __name__ == "__main__":
    main()
