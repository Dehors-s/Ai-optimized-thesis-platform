"""正文数字反查：每个数字必须落到证据台账的一条记录。

用法：
  py tools/number_check.py --dir projects/x
  py tools/number_check.py --text outputs/xxx.md --store projects/x/evidence/evidence.jsonl

与 check_project 里“数字在 facts.md 文本中出现过”不同，这里查的是
“这个数字对应哪条证据记录”，比较的是数值而不是子串。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

NUM_TEXT = re.compile(r"\d+\.\d{2,4}|\d{4,}")
CITE = re.compile(r"\[\d+(?:\s*[-,–]\s*\d+)*\]")
EMARK = re.compile(r"\[E-\d{4}\]")


def load_store(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def ledger_values(rows: list[dict]) -> dict[float, list[str]]:
    out: dict[float, list[str]] = {}
    for r in rows:
        if r.get("type") != "number":
            continue
        for tok in re.findall(r"\d+(?:\.\d+)?", str(r.get("value", ""))):
            try:
                out.setdefault(float(tok), []).append(r.get("id", ""))
            except ValueError:
                pass
    return out


def nums_in(text: str) -> list[str]:
    text = EMARK.sub(" ", text)
    text = CITE.sub(" ", text)
    return NUM_TEXT.findall(text)


def same(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


def check(rows: list[dict], ms: str) -> dict:
    values = ledger_values(rows)
    body = ms.split("## 参考文献")[0]
    found = nums_in(body)

    missing, years = [], []
    for tok in found:
        try:
            v = float(tok)
        except ValueError:
            continue
        if len(tok) == 4 and tok.isdigit() and 1900 <= v <= 2099:
            years.append(tok)
            continue
        if not any(same(v, k) for k in values):
            missing.append(tok)

    used = set()
    for tok in found:
        try:
            v = float(tok)
        except ValueError:
            continue
        for k in values:
            if same(v, k):
                used.add(k)

    unused = [(k, ids) for k, ids in values.items() if k not in used]

    # 摘要里的数字，正文必须也出现（摘要不能凭空多出数）
    warns = []
    m = re.search(r"(?m)^##\s*摘要\s*$", body)
    if m:
        nxt = re.search(r"(?m)^##\s+", body[m.end():])
        abs_text = body[m.end():m.end() + (nxt.start() if nxt else len(body))]
        rest = body[:m.start()] + body[m.end():]
        for tok in set(nums_in(abs_text)):
            try:
                v = float(tok)
            except ValueError:
                continue
            if not any(same(v, float(x)) for x in nums_in(rest)):
                warns.append(f"摘要里的 {tok} 在正文没有对应")

    fails = []
    if missing:
        fails.append(f"正文有 {len(missing)} 个数字在台账里找不到：{sorted(set(missing))[:12]}")
    if not rows:
        fails.append("证据台账为空")

    return {"n_text": len(found), "n_ledger": len(values),
            "missing": sorted(set(missing)), "unused": unused,
            "years": len(years), "fails": fails, "warns": warns}


def render_md(r: dict) -> str:
    lines = ["## 14 数字反查", "",
             f"- 正文数字 {r['n_text']} 个（年份 {r['years']} 个不计），台账数值 {r['n_ledger']} 个"]
    if r["missing"]:
        lines.append("- **台账中找不到**：" + "、".join(r["missing"][:15]))
    if r["unused"]:
        sample = "、".join(f"{k}（{','.join(v)}）" for k, v in r["unused"][:8])
        lines.append(f"- 台账里有、正文没用：{len(r['unused'])} 个，如 {sample}")
    if r["fails"]:
        lines.append("- 未通过：" + "；".join(r["fails"]))
    if r["warns"]:
        lines.append("- 提示：" + "；".join(r["warns"]))
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="")
    ap.add_argument("--text", default="")
    ap.add_argument("--store", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.dir:
        d = Path(args.dir)
        store = d / "evidence" / "evidence.jsonl"
        ms = (d / "manuscript.md").read_text(encoding="utf-8")
    else:
        if not (args.text and args.store):
            raise SystemExit("要么 --dir，要么 --text + --store")
        store = Path(args.store)
        ms = Path(args.text).read_text(encoding="utf-8")

    r = check(load_store(store), ms)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(render_md(r))
    sys.exit(0 if not r["fails"] else 1)


if __name__ == "__main__":
    main()
