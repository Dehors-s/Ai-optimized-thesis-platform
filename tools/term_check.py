"""扫描论文中的自造词/工程黑话，给出白话含义与替换建议。

用法：py tools/term_check.py --text outputs/双高论文_全文_v1.md
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

TERMS = {
    "闸门": ("提交前的校验步骤", "提交前校验"),
    "探针": ("每次线上提交的记录", "线上提交记录"),
    "写穿": ("后处理直接改写代理指标覆盖的像元，使指标失真", "代理指标被后处理直接改写而失真"),
    "数据侧": ("数据检查、预处理与表示", "数据与预处理环节"),
    "模型侧": ("骨干与集成", "模型与集成环节"),
    "推理侧": ("推理与后处理", "推理与后处理环节"),
    "输出侧": ("决策与提交", "输出与提交环节"),
    "增量账本": ("每次改动的读数与差", "增量记录表"),
    "账本": ("记录表", "记录表"),
    "恒等式段": ("可按指标定义精确分解的部分", "可精确分解的部分"),
    "探针段": ("线上实测、含噪声的增量", "实测增量（含噪声）"),
    "挖潜": ("从数据中找可用信息", "数据检查与利用"),
    "出包": ("生成并提交文件", "生成提交文件"),
    "口径": ("归一化方案", "归一化方案"),
    "底座": ("当前基线或前一版配置", "基线"),
    "拆账": ("指标分解", "指标分解"),
    "剂量": ("配额比例", "配额比例"),
    "份额": ("被判为未知类的像元比例", "配额比例"),
    "七阶段": ("七个处理步骤", "七个处理步骤"),
    "写穿指标": ("代理指标失真", "代理指标失真"),
}

VARIANTS = {
    "未知类比例": ["份额", "配额", "剂量", "比例"],
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    p = Path(args.text)
    t = p.read_text(encoding="utf-8")

    rows = []
    for term, (meaning, repl) in TERMS.items():
        n = t.count(term)
        if not n:
            continue
        ctx = []
        for m in list(re.finditer(re.escape(term), t))[:2]:
            s = re.sub(r"\s+", " ", t[max(0, m.start() - 28):m.end() + 28])
            ctx.append(s)
        rows.append((term, n, meaning, repl, ctx))

    rows.sort(key=lambda x: -x[1])
    total = sum(r[1] for r in rows)
    zh = len(re.findall(r"[\u4e00-\u9fff]", t)) or 1

    lines = [
        f"# 术语体检：{p.name}",
        "",
        f"- 字符数：{len(t)}；汉字数：{zh}",
        f"- 命中自造词/黑话：{total} 次，{total / zh * 1000:.1f} 次/千汉字",
        "",
        "| 词 | 次数 | 实际意思 | 建议写法 |",
        "|---|---|---|---|",
    ]
    for term, n, meaning, repl, _ in rows:
        lines.append(f"| {term} | {n} | {meaning} | {repl} |")
    lines += ["", "## 上下文", ""]
    for term, n, _, _, ctx in rows:
        lines.append(f"### {term}（{n} 次）")
        lines += [f"- {c}" for c in ctx]
        lines.append("")

    out = Path(args.out) if args.out else p.with_name(p.stem + "_术语体检.md")
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:12]))
    print("written", out)


if __name__ == "__main__":
    main()
