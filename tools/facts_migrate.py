"""把 facts.md 迁移成证据台账（evidence.jsonl）。

用法：
  py tools/facts_migrate.py --dir projects/x --dry-run
  py tools/facts_migrate.py --dir projects/x

迁移后的记录 `status=user_asserted`、`source.kind=file`：
它们来自作者提供的事实清单，但没有绑定实验 run id，所以不能当作机器核验。
后续可以用 evidence_store add 补 run id，再把旧记录标 superseded。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from evidence_store import load as load_ev, save as save_ev, next_id  # noqa: E402

NUM = re.compile(r"\d+(?:\.\d+)?")


def parse_facts(text: str) -> list[dict]:
    out: list[dict] = []
    section = ""
    table: list[list[str]] = []

    def flush_table() -> None:
        nonlocal table
        if len(table) >= 3:
            header = table[0]
            for row in table[2:]:
                label = row[0].strip() if row else ""
                for j, cell in enumerate(row[1:], 1):
                    m = NUM.search(cell)
                    if not m:
                        continue
                    head = header[j].strip() if j < len(header) else ""
                    claim = f"{label}（{head}）" if head else label
                    if not label and not head:
                        continue
                    out.append({"value": m.group(0), "claim": claim,
                                "section": section, "locator": f"{section} 表格"})
        table = []

    for line in text.splitlines():
        if line.startswith("## "):
            flush_table()
            section = line[3:].strip()
            continue
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            table.append(cells)
            continue
        flush_table()
        if line.strip().startswith("- "):
            body = line.strip()[2:]
            m = re.match(r"^([^：:]{1,40})[：:]\s*(.+)$", body)
            if not m:
                continue
            label, val = m.group(1).strip(), m.group(2).strip()
            if "规则" in section:
                continue
            nm = NUM.search(val)
            if nm:
                out.append({"value": nm.group(0), "claim": label,
                            "section": section, "locator": f"{section} 列表"})
    flush_table()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--keep-duplicates", action="store_true",
                    help="同一个数值也允许按不同 claim 再导入一条")
    args = ap.parse_args()

    d = Path(args.dir)
    facts = (d / "facts.md").read_text(encoding="utf-8")
    found = parse_facts(facts)

    rows = load_ev(d)
    have = {str(r.get("value")) for r in rows if r.get("value")}
    added = []
    for f in found:
        if args.keep_duplicates:
            key_ok = any(str(r.get("value")) == f["value"] and r.get("claim") == f["claim"] for r in rows)
            if key_ok:
                continue
        elif f["value"] in have:
            continue
        rec = {
            "id": next_id(rows + added),
            "type": "number",
            "claim": f["claim"],
            "value": f["value"],
            "unit": "",
            "source": {"kind": "file", "ref": "facts.md",
                       "locator": f.get("locator", ""), "url": "", "hash": ""},
            "validity": {"n": 0, "ci": []},
            "strength": "moderate",
            "status": "user_asserted",
            "notes": "由 facts.md 迁移，未绑定实验 run id",
        }
        added.append(rec)
        have.add(f["value"])

    if args.dry_run:
        print(f"可迁移 {len(added)} 条（已存在 {len(found) - len(added)} 条）")
        for r in added:
            print(f"  {r['id']}  {r['value']:>10}  {r['claim'][:60]}")
        return

    if added:
        save_ev(d, rows + added)
    print(f"migrated {len(added)} 条；台账现有 {len(rows) + len(added)} 条")


if __name__ == "__main__":
    main()
