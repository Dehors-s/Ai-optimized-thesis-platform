"""证据库：数字/表/图/引文/负结果的唯一来源，以及章节绑定检查。

用法：
  py tools/evidence_store.py init  --dir projects/x
  py tools/evidence_store.py add   --dir projects/x --type number --value 0.6584 \
      --unit macro-F1 --claim "重叠导致虚高" --source-kind experiment --source-ref run-a
  py tools/evidence_store.py list  --dir projects/x
  py tools/evidence_store.py check --dir projects/x

正文约定：每个断言句带 `[E-0001]`。检查器核对编号是否存在于库、是否属于本节
allowed、required 是否用到、是否用了 disputed 证据。

设计见 docs/17-证据库与引用流水线.md。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

TYPES = {"number", "table", "figure", "quote", "dataset", "code", "citation", "negative"}
STATUS = {"verified", "user_asserted", "disputed", "unverified"}
STRENGTH = {"strong", "moderate", "weak"}
MARK = re.compile(r"\[E-(\d{4})\]")


def store_path(d: Path) -> Path:
    return d / "evidence" / "evidence.jsonl"


def load(d: Path) -> list[dict]:
    p = store_path(d)
    if not p.exists():
        return []
    out = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise SystemExit(f"evidence.jsonl 第 {i} 行不是合法 JSON：{e}")
    return out


def save(d: Path, rows: list[dict]) -> None:
    p = store_path(d)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def next_id(rows: list[dict]) -> str:
    n = 0
    for r in rows:
        m = re.match(r"E-(\d{4})", str(r.get("id", "")))
        if m:
            n = max(n, int(m.group(1)))
    return f"E-{n + 1:04d}"


def sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def extract(ms: str, title: str) -> str | None:
    m = re.search(r"(?m)^##\s+" + re.escape(title) + r"\s*$", ms)
    if not m:
        return None
    start = m.end()
    nxt = re.search(r"(?m)^##\s+", ms[start:])
    return ms[start:start + nxt.start()] if nxt else ms[start:]


def check(rows: list[dict], manuscript: str, cfg: dict) -> dict:
    ids = [r.get("id", "") for r in rows]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    by_id = {r.get("id"): r for r in rows}
    binding = cfg.get("evidence", {}) or {}
    allowed_map = binding.get("allowed", {}) or {}
    required_map = binding.get("required", {}) or {}
    min_map = binding.get("min_units", {}) or {}

    fails: list[str] = []
    warns: list[str] = []
    rows_out: list[dict] = []
    used_all: set[str] = set()

    if dup:
        fails.append(f"证据 ID 重复：{dup}")
    if not rows:
        fails.append("证据库为空")

    sections = cfg.get("sections", [])
    for s in sections:
        title = s.get("title")
        if not title:
            continue
        text = extract(manuscript, title)
        if text is None:
            continue
        used = [f"E-{m}" for m in MARK.findall(text)]
        uniq = list(dict.fromkeys(used))
        used_all.update(uniq)

        undefined = [u for u in uniq if u not in by_id]
        allowed = allowed_map.get(title)
        over = [u for u in uniq if allowed is not None and u not in allowed]
        missing = [u for u in (required_map.get(title) or []) if u not in uniq]
        need = int(min_map.get(title) or 0)
        short = need - len(uniq)
        disputed = [u for u in uniq if (by_id.get(u, {}).get("status") == "disputed")]
        asserted = [u for u in uniq if (by_id.get(u, {}).get("status") == "user_asserted")]

        if undefined:
            fails.append(f"{title}：用了不存在的证据 {undefined}")
        if over:
            fails.append(f"{title}：用了本节不允许的证据 {over}")
        if missing:
            fails.append(f"{title}：必需证据未使用 {missing}")
        if short > 0:
            fails.append(f"{title}：证据数 {len(uniq)} < min_units {need}")
        if disputed:
            fails.append(f"{title}：使用了 disputed 证据 {disputed}，须作者裁决")
        if asserted:
            warns.append(f"{title}：使用了用户断言 {asserted}，表述需降级")

        rows_out.append({
            "section": title, "markers": len(uniq),
            "undefined": undefined, "over": over, "missing": missing,
            "short": max(0, short), "disputed": disputed, "asserted": asserted,
        })

    unused = [i for i in ids if i not in used_all]
    if unused:
        warns.append(f"从未被使用的证据 {len(unused)} 条：{unused[:10]}")

    # 库自身完整性
    for r in rows:
        if r.get("type") not in TYPES:
            fails.append(f"{r.get('id')}：type 不合法 {r.get('type')}")
        if r.get("status") not in STATUS:
            fails.append(f"{r.get('id')}：status 不合法 {r.get('status')}")
        if r.get("strength") and r["strength"] not in STRENGTH:
            fails.append(f"{r.get('id')}：strength 不合法 {r.get('strength')}")
        if not (r.get("claim") or r.get("value")):
            fails.append(f"{r.get('id')}：claim 与 value 都为空")

    return {"rows": rows_out, "fails": fails, "warns": warns,
            "count": len(rows), "used": len(used_all)}


def render_md(r: dict) -> str:
    lines = ["## 12 证据", ""]
    lines.append(f"- 证据 {r['count']} 条，被正文使用 {r['used']} 条")
    if r["rows"]:
        lines += ["", "| 节 | 标记数 | 未定义 | 越权 | 必需未用 | 缺口 |", "|---|---|---|---|---|---|"]
        for x in r["rows"]:
            if not x["markers"] and not x["missing"] and not x["short"]:
                continue
            lines.append(f"| {x['section']} | {x['markers']} | {'、'.join(x['undefined']) or '—'} | "
                         f"{'、'.join(x['over']) or '—'} | {'、'.join(x['missing']) or '—'} | {x['short'] or '—'} |")
    if r["fails"]:
        lines += ["", "- 未通过：" + "；".join(r["fails"])]
    if r["warns"]:
        lines += ["- 提示：" + "；".join(r["warns"])]
    lines.append("")
    return "\n".join(lines)


def cmd_init(d: Path) -> None:
    p = store_path(d)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text("", encoding="utf-8")
    (d / "evidence" / "README.md").write_text(
        "# 证据库\n\n一行一条 JSON，字段见 docs/17。\n正文用 `[E-0001]` 引用；"
        "`project.json` 的 `evidence.allowed/required/min_units` 决定每节能用哪些。\n",
        encoding="utf-8")
    print(f"ok {p}")


def cmd_add(d: Path, args: argparse.Namespace) -> None:
    rows = load(d)
    rid = args.id or next_id(rows)
    if any(r.get("id") == rid for r in rows):
        raise SystemExit(f"ID 已存在：{rid}")
    ci = [float(x) for x in args.ci.split(",")] if args.ci else []
    rec = {
        "id": rid,
        "type": args.type,
        "claim": args.claim,
        "value": args.value,
        "unit": args.unit,
        "source": {"kind": args.source_kind, "ref": args.source_ref,
                   "locator": args.source_locator, "url": args.source_url,
                   "hash": sha(f"{args.source_ref}|{args.source_locator}|{args.value}")},
        "validity": {"n": args.n, "ci": ci},
        "strength": args.strength,
        "status": args.status,
        "notes": args.notes,
    }
    rows.append(rec)
    save(d, rows)
    print(f"added {rid} ({rec['type']}, {rec['status']})")


def cmd_list(d: Path) -> None:
    rows = load(d)
    if not rows:
        print("（空）")
        return
    print("| id | type | value | unit | status | claim |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r.get('id')} | {r.get('type')} | {r.get('value')} | {r.get('unit')} | "
              f"{r.get('status')} | {str(r.get('claim'))[:40]} |")


def cmd_check(d: Path) -> None:
    cfg = {}
    if (d / "project.json").exists():
        cfg = json.loads((d / "project.json").read_text(encoding="utf-8"))
    ms_path = d / "manuscript.md"
    if not ms_path.exists():
        raise SystemExit("缺少 manuscript.md")
    rows = load(d)
    r = check(rows, ms_path.read_text(encoding="utf-8"), cfg)
    md = render_md(r)
    out = d / "checks" / "evidence_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# 证据检查\n\n" + md, encoding="utf-8")
    print(md)
    sys.exit(0 if not r["fails"] else 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.add_argument("--dir", required=True)

    p = sub.add_parser("add")
    p.add_argument("--dir", required=True)
    p.add_argument("--type", required=True, choices=sorted(TYPES))
    p.add_argument("--claim", default="")
    p.add_argument("--value", default="")
    p.add_argument("--unit", default="")
    p.add_argument("--source-kind", default="experiment",
                   choices=["experiment", "file", "url", "user"])
    p.add_argument("--source-ref", default="")
    p.add_argument("--source-locator", default="")
    p.add_argument("--source-url", default="")
    p.add_argument("--status", default="verified", choices=sorted(STATUS))
    p.add_argument("--strength", default="moderate", choices=sorted(STRENGTH))
    p.add_argument("--n", type=int, default=0)
    p.add_argument("--ci", default="")
    p.add_argument("--notes", default="")
    p.add_argument("--id", default="")

    p = sub.add_parser("list")
    p.add_argument("--dir", required=True)

    p = sub.add_parser("check")
    p.add_argument("--dir", required=True)

    args = ap.parse_args()
    d = Path(args.dir)
    if args.cmd == "init":
        cmd_init(d)
    elif args.cmd == "add":
        cmd_add(d, args)
    elif args.cmd == "list":
        cmd_list(d)
    else:
        cmd_check(d)


if __name__ == "__main__":
    main()
