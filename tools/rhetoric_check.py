"""修辞体检：抓 AI 写作里最常见、审稿人最反感的几种句式。

用法：
  py tools/rhetoric_check.py --text outputs/xxx.md
  py tools/rhetoric_check.py --text outputs/xxx.md --json

设计依据：
- The rise of antithesis (arXiv:2610.10092)：LLM 让“不是…而是/而非”式对偶
  在 ACL 论文里涨了 7 倍，约一半 2026 论文至少一处让审稿人反感；
  偏好数据和奖励模型反而奖励这种写法。
- Accelerated drift of scientific prose (arXiv:2610.26008)：单一词频标记
  只能解释一部分漂移，需多维监测。
- HoWToBench (arXiv:2604.19071)：LLM 评委对文本扰动脆弱，需可核验规则。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CJK = re.compile(r"[\u4e00-\u9fff]")

PATTERNS = [
    ("对偶否定", r"不是[^。！？\n]{0,40}?而是", "不是…而是", 2.0),
    ("对偶否定", r"并非[^。！？\n]{0,40}?而是", "并非…而是", 2.0),
    ("对偶否定", r"而非", "而非", 2.0),
    ("对偶否定", r"与其[^。！？\n]{0,30}?不如", "与其…不如", 2.0),
    ("空枚举", r"(?m)^\s*(首先|其次|再次|最后)[，,、]", "段首首先/其次", 1.5),
    ("空枚举", r"一方面[^。]{0,60}?另一方面", "一方面…另一方面", 1.5),
    ("元话语", r"值得注意的是|需要指出的是|不难发现|众所周知|毋庸置疑", "值得注意/众所周知", 1.0),
    ("元话语", r"综上所述|总而言之|总的来说|由此可见", "综上/由此可见", 1.0),
    ("空强调", r"具有重要意义|具有重要价值|意义重大|至关重要", "意义重大", 1.0),
    ("空强调", r"极大地?|显著地?提升|有效提升|大幅提升", "极大/显著提升", 0.0),
    ("三段式", r"不仅[^。！？\n]{0,40}?而且", "不仅…而且", 1.0),
    ("三段式", r"既[^。！？\n]{0,25}?又", "既…又", 1.0),
]

# 句子里有这些，说明在为判断提供依据
EVIDENCE = re.compile(r"[0-9０-９]|\[\d|%|第\s*\d|图\s*\d|表\s*\d|因为|由于|使得|导致|取决于|来自|可由|可由下式|式中")
MECHANISM_OK = re.compile(r"因为|由于|使得|导致|取决于|等价于|意味着|即|可由|式中")


def split_sents(t: str) -> list[str]:
    t = re.sub(r"(?m)^#.*$", "", t)
    t = re.sub(r"(?m)^\|.*$", "", t)
    return [s.strip() for s in re.split(r"(?<=[。！？])", t) if len(CJK.findall(s)) >= 8]


def check(text: str) -> dict:
    zh = len(CJK.findall(text)) or 1
    sents = split_sents(text)
    hits = []
    for group, pat, label, weight in PATTERNS:
        for m in re.finditer(pat, text):
            hits.append({"group": group, "label": label, "match": m.group(0)[:40],
                         "weight": weight, "pos": m.start()})

    by_label: dict[str, int] = {}
    for h in hits:
        by_label[h["label"]] = by_label.get(h["label"], 0) + 1

    no_ev = [s for s in sents if not EVIDENCE.search(s)]

    # 相邻句重复开头（排比式空转）
    opens: dict[str, int] = {}
    for s in sents:
        head = re.sub(r"^[，。、；：\s]+", "", s)[:4]
        if len(CJK.findall(head)) >= 3:
            opens[head] = opens.get(head, 0) + 1
    repeated_opens = {k: v for k, v in opens.items() if v >= 4}

    ne_ratio = round(len(no_ev) / len(sents), 3) if sents else 0.0
    antithesis = sum(v for k, v in by_label.items() if k in ("不是…而是", "并非…而是", "而非", "与其…不如"))
    anti_per_1000 = round(antithesis / zh * 1000, 2)
    meta = sum(v for k, v in by_label.items() if k in ("值得注意/众所周知", "综上/由此可见", "意义重大"))
    empty_enum = sum(v for k, v in by_label.items() if k in ("段首首先/其次", "一方面…另一方面"))

    fails, warns = [], []
    if anti_per_1000 > 2.0:
        fails.append(f"对偶否定 {anti_per_1000}/千字，超过 2")
    elif anti_per_1000 > 1.0:
        warns.append(f"对偶否定 {anti_per_1000}/千字，偏多")
    if meta > 2:
        warns.append(f"元话语/空强调 {meta} 处")
    if empty_enum > 2:
        warns.append(f"空枚举 {empty_enum} 处")
    if ne_ratio > 0.65:
        warns.append(f"无证据句 {ne_ratio:.0%}，接近纯叙述")
    if repeated_opens:
        warns.append("重复开头：" + "、".join(f"{k}×{v}" for k, v in repeated_opens.items()))

    return {
        "zh_chars": zh,
        "sentences": len(sents),
        "hits": hits,
        "by_label": by_label,
        "per_1000": {k: round(v / zh * 1000, 2) for k, v in by_label.items()},
        "antithesis_per_1000": anti_per_1000,
        "no_evidence_sents": len(no_ev),
        "no_evidence_ratio": ne_ratio,
        "repeated_openings": repeated_opens,
        "fails": fails,
        "warns": warns,
        "verdict": "fail" if fails else ("warn" if warns else "pass"),
    }


def render_md(r: dict) -> str:
    lines = ["## 10 修辞", ""]
    lines.append(f"- 汉字 {r['zh_chars']}，句 {r['sentences']}，判定 **{r['verdict']}**")
    if r["by_label"]:
        lines.append("- 命中：" + "；".join(f"{k} {v} 次（{r['per_1000'][k]}/千字）" for k, v in r["by_label"].items()))
    else:
        lines.append("- 未命中对偶/空枚举/元话语")
    lines.append(f"- 对偶否定密度：{r['antithesis_per_1000']}/千字（阈值 1 提示、2 未通过）")
    lines.append(f"- 无证据句（无数字、无引用、无因为/由于/使得）：{r['no_evidence_sents']} 句（{r['no_evidence_ratio']:.0%}）")
    if r["repeated_openings"]:
        lines.append("- 重复开头：" + "、".join(f"“{k}”×{v}" for k, v in r["repeated_openings"].items()))
    if r["fails"]:
        lines.append("- 未通过：" + "；".join(r["fails"]))
    if r["warns"]:
        lines.append("- 提示：" + "；".join(r["warns"]))
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    text = Path(args.text).read_text(encoding="utf-8")
    r = check(text)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(render_md(r))
    sys.exit(0 if r["verdict"] != "fail" else 1)


if __name__ == "__main__":
    main()
