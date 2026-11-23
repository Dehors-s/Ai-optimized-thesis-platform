"""新建论文项目：按论文类型复制模板，按期刊×语言×学科解析画像。

用法：
  py tools/new_project.py --name "某论文" --dir projects/xxx --title "题目" \
      --type empirical --journal 测绘学报 --language zh --discipline remote_sensing
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "paperkit" / "templates"
sys.path.insert(0, str(ROOT / "tools"))
from profile_registry import resolve  # noqa: E402

TYPES = {
    "empirical": {
        "sections": [
            {"title": "摘要", "role": "abstract"},
            {"title": "1 引言", "role": "intro"},
            {"title": "2 相关工作", "role": "related"},
            {"title": "3 问题、数据与评测", "role": "problem"},
            {"title": "4 方法", "role": "method"},
            {"title": "5 实验", "role": "results"},
            {"title": "6 讨论", "role": "discussion"},
            {"title": "7 结论", "role": "conclusion"},
        ],
        "decomposition": {"name": "按方法组件分解", "items": []},
    },
    "engineering": {
        "sections": [
            {"title": "摘要", "role": "abstract"},
            {"title": "1 引言", "role": "intro"},
            {"title": "2 问题与数据检查", "role": "problem"},
            {"title": "3 方法一（分解项 1）", "role": "method"},
            {"title": "4 方法二（分解项 2）", "role": "method"},
            {"title": "5 方法三（分解项 3）", "role": "method"},
            {"title": "6 实验与结果", "role": "results"},
            {"title": "7 讨论", "role": "discussion"},
            {"title": "8 结论", "role": "conclusion"},
        ],
        "decomposition": {"name": "按误差位置分解（示例）", "items": ["数据检查", "数据预处理", "异构骨干", "训练后处理"]},
    },
    "survey": {
        "sections": [
            {"title": "摘要", "role": "abstract"},
            {"title": "1 引言", "role": "intro"},
            {"title": "2 检索与分类框架", "role": "taxonomy"},
            {"title": "3 方法族对比", "role": "comparison"},
            {"title": "4 挑战", "role": "challenges"},
            {"title": "5 展望", "role": "outlook"},
            {"title": "6 结论", "role": "conclusion"},
        ],
        "decomposition": {"name": "按分类维度分解", "items": []},
    },
    "systems": {
        "sections": [
            {"title": "摘要", "role": "abstract"},
            {"title": "1 引言", "role": "intro"},
            {"title": "2 相关工作", "role": "related"},
            {"title": "3 问题与需求", "role": "problem"},
            {"title": "4 系统设计", "role": "method"},
            {"title": "5 实现", "role": "method"},
            {"title": "6 评估", "role": "results"},
            {"title": "7 讨论", "role": "discussion"},
            {"title": "8 结论", "role": "conclusion"},
        ],
        "decomposition": {"name": "按系统组件分解", "items": []},
    },
    "theory": {
        "sections": [
            {"title": "摘要", "role": "abstract"},
            {"title": "1 引言", "role": "intro"},
            {"title": "2 相关工作", "role": "related"},
            {"title": "3 问题形式化", "role": "problem"},
            {"title": "4 理论分析", "role": "method"},
            {"title": "5 结果与讨论", "role": "discussion"},
            {"title": "6 结论", "role": "conclusion"},
        ],
        "decomposition": {"name": "按定理/引理分解", "items": []},
    },
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--title", default="论文题目（待定）")
    ap.add_argument("--type", default="empirical", choices=list(TYPES))
    ap.add_argument("--mode", default="project", choices=["template", "project"])
    ap.add_argument("--journal", default="")
    ap.add_argument("--language", default="zh", choices=["zh", "en"])
    ap.add_argument("--discipline", default="")
    args = ap.parse_args()

    out = Path(args.dir)
    if out.exists():
        raise SystemExit(f"目录已存在：{out}")
    for sub in ["checks", "figures/spec", "refs", "evidence"]:
        (out / sub).mkdir(parents=True, exist_ok=True)
    (out / "evidence" / "evidence.jsonl").write_text("", encoding="utf-8")
    (out / "refs" / "refs.jsonl").write_text("", encoding="utf-8")

    mapping = {"{{NAME}}": args.name, "{{TITLE}}": args.title,
               "{{DATE}}": datetime.date.today().isoformat(),
               "{{TYPE}}": args.type, "{{MODE}}": args.mode}

    for name in ["facts.md", "paper_ir.json"]:
        text = (TPL / "generic" / name).read_text(encoding="utf-8")
        for k, v in mapping.items():
            text = text.replace(k, v)
        (out / name).write_text(text, encoding="utf-8")

    if args.mode == "project":
        text = (TPL / "generic" / "innovation.md").read_text(encoding="utf-8")
        (out / "innovation.md").write_text(text, encoding="utf-8")

    tdir = TPL / "types" / args.type
    for name in ["outline.md", "manuscript.md"]:
        text = (tdir / name).read_text(encoding="utf-8")
        for k, v in mapping.items():
            text = text.replace(k, v)
        (out / name).write_text(text, encoding="utf-8")

    profiles = resolve(args.journal, args.language, args.discipline)
    sections = []
    for s in TYPES[args.type]["sections"]:
        s = dict(s)
        if s.get("role") in ("method", "results", "discussion"):
            s["profile"] = (profiles or {}).get(s["role"])
        sections.append(s)

    cfg = {
        "name": args.name,
        "paper_type": args.type,
        "mode": args.mode,
        "language": args.language,
        "journal": args.journal,
        "discipline": args.discipline,
        "profiles": profiles,
        "sections": sections,
        "decomposition": TYPES[args.type]["decomposition"],
        "evidence": {"allowed": {}, "required": {}, "min_units": {}},
        "citation_slots": {},
        "rules": {
            "forbidden_phrases": ["优于", "高于对照", "纯自研", "证明了"],
            "required_attribution": None,
            "required_statements": [],
        },
    }
    (out / "project.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"created {out} ({args.type}, {args.language}, journal={args.journal or '未指定'})")
    if not profiles:
        print("警告：未找到画像，语体检查将跳过；可在 project.json 手动指定。")
    print("下一步：1) 填 facts.md  2) 定 paper_ir.json  3) 改 outline.md  4) 写 manuscript.md")


if __name__ == "__main__":
    main()
