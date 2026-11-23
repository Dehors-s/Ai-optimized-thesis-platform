"""统计全文「方法叙事」的结构特征：引言如何立方法、方法节如何串设计、结果如何回收。

用法：py tools/analyze_method_narrative.py
输出：corpus/method_narrative_report.md
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_section_profiles import split_sections, normalize, sents, zh_ratio  # noqa

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
DIRS = {"rs": CORPUS / "text" / "xb", "cs": CORPUS / "text" / "aas"}
OUT = CORPUS / "method_narrative_report.md"

PROBLEM = ["针对", "为了", "由于", "鉴于", "考虑到", "面临", "难点", "挑战", "不足", "受限"]
MECH = ["因为", "由于", "从而", "使得", "以便", "目的是", "核心思想", "本质", "原因", "之所以"]
OPER = ["采用", "使用", "设置", "训练", "选取", "调整", "配置", "输入", "输出"]
CONTRIB = ["本文提出", "本文构建", "本文设计", "本文给出", "本文采用", "提出一种", "构建一种", "设计一种"]
RESULT = ["结果表明", "结果显示", "实验表明", "验证了", "所提方法", "该方法", "如图", "见表"]


def rate(text: str, words: list[str]) -> float:
    return round(sum(text.count(w) for w in words) * 10000 / max(len(text), 1), 1)


def first_sent(p: str) -> str:
    ss = sents(p)
    return ss[0] if ss else ""


def main() -> None:
    report: dict = {}
    samples: dict[str, list[str]] = {"method_first": [], "intro_contrib": [], "results_first": []}
    for domain, d in DIRS.items():
        stat = {k: Counter() for k in ["sections", "method_para_first", "intro_contrib", "results_first"]}
        texts = {k: [] for k in ["intro", "method", "results"]}
        for p in d.glob("*.txt"):
            try:
                t = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            secs = split_sections(t)
            for k in texts:
                if k in secs and len(secs[k]) > 300:
                    texts[k].append(normalize(secs[k]))
        for k, arr in texts.items():
            stat["sections"][k] = len(arr)
        all_method = "\n".join(texts["method"])
        all_intro = "\n".join(texts["intro"])
        all_results = "\n".join(texts["results"])

        # 方法节：每个自然段首句的模式
        for doc in texts["method"]:
            for para in re.split(r"\n\s*\n", doc):
                fs = first_sent(para)
                if not fs:
                    continue
                for w in PROBLEM:
                    if fs.startswith(w) or w in fs[:20]:
                        stat["method_para_first"][f"问题:{w}"] += 1
                        break
                else:
                    stat["method_para_first"]["直述"] += 1
                if len(samples["method_first"]) < 12 and (fs.startswith("针对") or fs.startswith("为了")):
                    samples["method_first"].append(f"[{domain}] {fs[:90]}")

        # 引言：贡献句
        for doc in texts["intro"]:
            for s in sents(doc):
                if any(w in s for w in CONTRIB):
                    stat["intro_contrib"]["贡献句"] += 1
                    if len(samples["intro_contrib"]) < 10:
                        samples["intro_contrib"].append(f"[{domain}] {s[:100]}")
                elif any(w in s for w in ["实验", "结果", "提升"]):
                    stat["intro_contrib"]["结果句"] += 1

        # 结果节：首句模式
        for doc in texts["results"]:
            for para in re.split(r"\n\s*\n", doc):
                fs = first_sent(para)
                if not fs:
                    continue
                if any(w in fs for w in ["图", "表"]):
                    stat["results_first"]["图表"] += 1
                elif any(w in fs for w in ["表明", "显示", "验证"]):
                    stat["results_first"]["结论"] += 1
                elif re.search(r"0\.\d|\d+%|\d+\s*个", fs):
                    stat["results_first"]["数字"] += 1
                else:
                    stat["results_first"]["其他"] += 1
                if len(samples["results_first"]) < 8:
                    samples["results_first"].append(f"[{domain}] {fs[:90]}")

        report[domain] = {
            "n": stat["sections"],
            "problem_rate_per_10k": rate(all_method, PROBLEM),
            "mech_rate_per_10k": rate(all_method, MECH),
            "oper_rate_per_10k": rate(all_method, OPER),
            "problem_para_first": stat["method_para_first"].most_common(8),
            "intro_contrib": dict(stat["intro_contrib"]),
            "results_first": dict(stat["results_first"]),
        }

    lines = ["# 方法叙事结构统计（全文）", ""]
    for domain, d in report.items():
        lines += [
            f"## {domain}", "",
            f"- 节数：{d['n']}",
            f"- 方法节：问题标记 {d['problem_rate_per_10k']}/万字，机制标记 {d['mech_rate_per_10k']}/万字，操作标记 {d['oper_rate_per_10k']}/万字",
            f"- 方法节段首模式：{d['problem_para_first']}",
            f"- 引言贡献/结果句：{d['intro_contrib']}",
            f"- 结果节段首：{d['results_first']}",
            "",
        ]
    lines += ["## 样例", ""]
    for k, arr in samples.items():
        lines.append(f"### {k}")
        lines += [f"- {x}" for x in arr[:10]]
        lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2)[:3000])


if __name__ == "__main__":
    main()
