"""按“文章角色”给现有图分类，并对照顶刊蓝图输出缺口清单。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MS = ROOT / "projects" / "双高2026" / "manuscript.md"
GAP = ROOT / "projects" / "双高2026" / "checks" / "corpus_gap.json"
OUT = ROOT / "projects" / "双高2026" / "checks" / "figure_plan.md"

TYPE_KW = {
    "architecture": ["框架", "架构", "流程", "网络结构", "模块", "成员池", "融合式"],
    "map": ["地图", "研究区", "空间分布", "航线", "瓦片分布"],
    "qualitative": ["分类结果", "定性", "误差图", "目视", "场景"],
    "distribution": ["构成", "分布", "漏斗", "增量", "平台", "收益", "配额", "窗宽", "上限"],
    "scatter": ["散点", "相关", "对比", "AUC", "判据"],
}

BLUEPRINT = {
    "architecture": 1,
    "map": 1,
    "qualitative": 1,
    "distribution": 2,
    "scatter": 1,
}


def classify(caption: str) -> str:
    scores = {k: sum(1 for w in ws if w in caption) for k, ws in TYPE_KW.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "other"


def main() -> None:
    t = MS.read_text(encoding="utf-8")
    figs = []
    for m in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", t):
        figs.append((m.group(1), m.group(2), classify(m.group(1))))
    counts = {}
    for _, _, typ in figs:
        counts[typ] = counts.get(typ, 0) + 1

    refs = max([int(x) for x in re.findall(r"\[(\d{1,3})\]", t)] or [0])
    tabs = len(re.findall(r"(?m)^\*\*表\s*\d+", t))
    zh = len(re.findall(r"[\u4e00-\u9fff]", t))

    corpus = {}
    if GAP.exists():
        corpus = json.loads(GAP.read_text(encoding="utf-8")).get("corpus", {})
    med_refs = sorted(v["refs_median"] for v in corpus.values())[len(corpus) // 2] if corpus else 33
    med_tabs = sorted(v["tabs_median"] for v in corpus.values())[len(corpus) // 2] if corpus else 3
    med_figs = sorted(v["figs_median"] for v in corpus.values())[len(corpus) // 2] if corpus else 8

    lines = ["# 图表缺口清单", ""]
    lines += [f"- 汉字：{zh}；图：{len(figs)}；表：{tabs}；参考文献：{refs}", ""]
    lines += ["## 现有图分类", "", "| 图 | 类型 | 文件 |", "|---|---|---|"]
    for cap, path, typ in figs:
        lines.append(f"| {cap[:28]} | {typ} | {path.split('/')[-1]} |")

    lines += ["", "## 与顶刊蓝图对比", "",
              "| 类型 | 现有 | 建议 | 缺口 |", "|---|---|---|---|"]
    missing = []
    for typ, need in BLUEPRINT.items():
        have = counts.get(typ, 0)
        gap = max(0, need - have)
        if gap:
            missing.append((typ, gap))
        lines.append(f"| {typ} | {have} | {need} | {gap} |")

    lines += ["", "## 硬指标", "",
              f"- 图：{len(figs)} vs 本地中位 {med_figs:g}",
              f"- 表：{tabs} vs 本地中位 {med_tabs:g}",
              f"- 参考文献：{refs} vs 本地中位 {med_refs:g}",
              ""]
    if len(figs) < med_figs:
        lines.append(f"- 图少 {med_figs - len(figs):g} 张")
    if tabs > med_tabs:
        lines.append(f"- 正文表多 {tabs - med_tabs:g} 张，建议移附录")
    if refs < med_refs:
        lines.append(f"- 参考文献少 {med_refs - refs:g} 条，优先补")

    if missing:
        lines += ["", "## 优先补的图", ""]
        for typ, gap in missing:
            need = {
                "map": "研究区/航线/瓦片覆盖图，需坐标或瓦片索引",
                "qualitative": "3—4 个场景的分类结果/误差图，需分类栅格",
                "distribution": "数据构成/漏斗/增量图，可由 facts 自动生成",
                "scatter": "SOTA 对比或判据点图，需基线或已有表",
                "architecture": "方法框架/成员池架构，可由 facts 自动生成",
            }[typ]
            lines.append(f"- **{typ}** 缺 {gap} 张：{need}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
