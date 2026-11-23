"""统计本地论文语料与我们的稿子，输出图表/篇幅/参考文献差距。"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
TEXT = ROOT / "corpus" / "text"
MS = ROOT / "projects" / "双高2026" / "manuscript.md"


def zh(s: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", s))


def stats(text: str) -> dict:
    # 图/表编号（中文期刊图注：图 1 / 表 1）
    figs = sorted({int(x) for x in re.findall(r"(?m)^\s*图\s*(\d+)", text)})
    tabs = sorted({int(x) for x in re.findall(r"(?m)^\s*表\s*(\d+)", text)})
    cites = [int(x) for x in re.findall(r"\[(\d{1,3})\]", text)]
    refs = max(cites) if cites else 0
    # 摘要汉字数
    m = re.search(r"摘\s*要(.{50,3000}?)(关键词|关键字)", text, re.S)
    abstract = zh(m.group(1)) if m else 0
    sections = len(re.findall(r"(?m)^\s*\d+\s+\S", text))
    return {"zh": zh(text), "figs": len(figs), "tabs": len(tabs),
            "refs": refs, "abstract_zh": abstract, "sections": sections}


def main() -> None:
    groups = defaultdict(list)
    for p in TEXT.rglob("*.txt"):
        t = p.read_text(encoding="utf-8", errors="ignore")
        if zh(t) < 2000:
            continue
        groups[p.parent.name].append(stats(t))
    print("journal\tn\tzh\tfigs\ttabs\trefs\tabstract\tsections")
    for k, rows in groups.items():
        n = len(rows)
        med = lambda key: median(r[key] for r in rows)
        print(f"{k}\t{n}\t{med('zh'):.0f}\t{med('figs')}\t{med('tabs')}\t"
              f"{med('refs')}\t{med('abstract_zh'):.0f}\t{med('sections')}")

    t = MS.read_text(encoding="utf-8")
    # 我们的图是 markdown 图片
    figs = len(re.findall(r"!\[", t))
    tabs = len(re.findall(r"(?m)^\*\*表\s*\d+", t))
    cites = [int(x) for x in re.findall(r"\[(\d{1,3})\]", t)]
    refs = max(cites) if cites else 0
    m = re.search(r"## 摘要\s*\n(.*?)\n## ", t, re.S)
    abstract = zh(m.group(1)) if m else 0
    print(f"ours\t1\t{zh(t)}\t{figs}\t{tabs}\t{refs}\t{abstract}\t9")

    out = ROOT / "projects" / "双高2026" / "checks" / "corpus_gap.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "corpus": {k: {
            "n": len(v),
            "zh_median": median(r["zh"] for r in v),
            "figs_median": median(r["figs"] for r in v),
            "tabs_median": median(r["tabs"] for r in v),
            "refs_median": median(r["refs"] for r in v),
            "abstract_median": median(r["abstract_zh"] for r in v),
        } for k, v in groups.items()},
        "ours": {"zh": zh(t), "figs": figs, "tabs": tabs, "refs": refs,
                 "abstract_zh": abstract, "sections": 9},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("written", out)


if __name__ == "__main__":
    main()
