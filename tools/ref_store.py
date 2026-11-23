"""文献库：真实文献记录、批量导入、编号对齐、槽位覆盖、按首次出现重编号。

用法：
  py tools/ref_store.py init       --dir projects/x
  py tools/ref_store.py import-gbt --dir projects/x --file refs/inbox.txt
  py tools/ref_store.py import-bib --dir projects/x --file refs/library.bib
  py tools/ref_store.py import-ris --dir projects/x --file refs/library.ris
  py tools/ref_store.py add        --dir projects/x --title "..." --year 2023 --venue "测绘学报"
  py tools/ref_store.py list       --dir projects/x
  py tools/ref_store.py check      --dir projects/x
  py tools/ref_store.py export     --dir projects/x [--apply]

设计见 docs/17-证据库与引用流水线.md。
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from ref_audit import cited_numbers, overlap, split_refs  # noqa: E402

TYPES = {"journal": "J", "conference": "C", "book": "M", "thesis": "D", "other": "EB/OL"}
STATUS = {"verified", "manual", "candidate", "weak", "retracted"}
INTENTS = {"background", "support", "contrast", "method_origin", "data_source", "limitation"}

CITE = re.compile(r"\[(\d+(?:\s*[-,–]\s*\d+)*)\]")
REF_ENTRY = re.compile(r"(?ms)^\[(\d+)\]\s*(.*?)(?=\n\s*\[\d+\]|\Z)")


def store_path(d: Path) -> Path:
    return d / "refs" / "refs.jsonl"


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
            raise SystemExit(f"refs.jsonl 第 {i} 行不是合法 JSON：{e}")
    return out


def save(d: Path, rows: list[dict]) -> None:
    p = store_path(d)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def next_id(rows: list[dict]) -> str:
    n = 0
    for r in rows:
        m = re.match(r"R-(\d{4})", str(r.get("id", "")))
        if m:
            n = max(n, int(m.group(1)))
    return f"R-{n + 1:04d}"


def norm_title(t: str) -> str:
    return re.sub(r"\W+", "", (t or "").lower())


# ---------------------------------------------------------------- 解析

GB = re.compile(
    r"^\s*(?:\[(\d+)\]\s*)?(.+?)\.\s*(.+?)\s*"
    r"\[(J|C|D|M|R|S|N|P|EB/OL|J/OL|C/OL)\]\s*\.?\s*(.*)$")


def parse_gbt(line: str) -> dict | None:
    m = GB.match(line.strip())
    if not m:
        return None
    _, authors, title, kind, tail = m.groups()
    year = re.search(r"(19|20)\d{2}", tail)
    venue = re.split(r"[,，]\s*(?:19|20)\d{2}", tail)[0].strip(" .;，,")
    vol = re.search(r"(\d+)\s*\((\d+)\)", tail)
    pages = re.search(r"(\d+)\s*[-–—]\s*(\d+)", tail)
    return {
        "authors": [a.strip() for a in re.split(r"[,，]", authors) if a.strip()],
        "title": title.strip(" ."),
        "type": {"J": "journal", "C": "conference", "D": "thesis", "M": "book"}.get(kind, "other"),
        "venue": venue,
        "year": int(year.group(0)) if year else None,
        "volume": int(vol.group(1)) if vol else None,
        "issue": int(vol.group(2)) if vol else None,
        "pages": f"{pages.group(1)}-{pages.group(2)}" if pages else "",
        "raw": line.strip(),
    }


BIB_ENTRY = re.compile(r"@(\w+)\s*\{\s*([^,]+),(.*?)\n\}", re.S)
BIB_FIELD = re.compile(r"(\w+)\s*=\s*[{\"](.*?)[}\"]\s*,?\s*\n", re.S)
BIB_KIND = {"article": "journal", "inproceedings": "conference", "conference": "conference",
            "book": "book", "phdthesis": "thesis", "mastersthesis": "thesis",
            "techreport": "other", "misc": "other"}


def parse_bib(text: str) -> list[dict]:
    out = []
    for kind, key, body in BIB_ENTRY.findall(text):
        f = {k.lower(): re.sub(r"\s+", " ", v).strip() for k, v in BIB_FIELD.findall(body)}
        title = f.get("title", "")
        if not title:
            continue
        year = re.search(r"\d{4}", f.get("year", "") or f.get("date", ""))
        out.append({
            "key": key.strip(),
            "authors": [a.strip() for a in re.split(r"\s+and\s+", f.get("author", "")) if a.strip()],
            "title": re.sub(r"[{}]", "", title),
            "year": int(year.group(0)) if year else None,
            "venue": re.sub(r"[{}]", "", f.get("journal") or f.get("booktitle") or ""),
            "type": BIB_KIND.get(kind.lower(), "other"),
            "doi": f.get("doi", ""),
            "arxiv": (f.get("eprint", "") if f.get("archiveprefix", "").lower() == "arxiv" else ""),
            "url": f.get("url", ""),
        })
    return out


def parse_ris(text: str) -> list[dict]:
    out, cur = [], {}

    def flush():
        if not cur:
            return
        title = cur.get("TI") or cur.get("T1") or ""
        if not title:
            cur.clear()
            return
        year = re.search(r"\d{4}", cur.get("PY", "") or cur.get("Y1", ""))
        ty = cur.get("TY", "")
        au = cur.get("AU", [])
        out.append({
            "authors": au if isinstance(au, list) else [au],
            "title": title,
            "year": int(year.group(0)) if year else None,
            "venue": cur.get("JO") or cur.get("JF") or cur.get("T2") or "",
            "type": {"JOUR": "journal", "CONF": "conference", "BOOK": "book",
                     "THES": "thesis"}.get(ty, "other"),
            "doi": cur.get("DO", ""),
            "url": cur.get("UR", ""),
        })
        cur.clear()

    for line in text.splitlines():
        m = re.match(r"^([A-Z][A-Z0-9])\s{2}-\s?(.*)$", line)
        if not m:
            continue
        tag, val = m.group(1), m.group(2).strip()
        if tag == "TY":
            cur["TY"] = val
        elif tag in ("TI", "T1"):
            cur["TI"] = val
        elif tag in ("AU", "A1"):
            cur.setdefault("AU", [])
            if isinstance(cur["AU"], list):
                cur["AU"].append(val)
        elif tag in ("PY", "Y1"):
            cur["PY"] = val
        elif tag in ("JO", "JF", "T2"):
            cur["JO"] = val
        elif tag == "DO":
            cur["DO"] = val
        elif tag == "UR":
            cur["UR"] = val
        elif tag == "ER":
            flush()
    flush()
    return out


# ---------------------------------------------------------------- 命令

def _add_many(d: Path, recs: list[dict], status: str) -> tuple[int, int]:
    rows = load(d)
    have_t = {norm_title(r.get("title", "")) for r in rows}
    have_d = {r.get("doi", "").lower() for r in rows if r.get("doi")}
    added = skipped = 0
    for rec in recs:
        t = norm_title(rec.get("title", ""))
        doi = (rec.get("doi") or "").lower()
        if (t and t in have_t) or (doi and doi in have_d):
            skipped += 1
            continue
        rec["id"] = next_id(rows)
        rec["status"] = status
        rec["provenance"] = {"verified_by": "import", "verified_at": datetime.date.today().isoformat()}
        rec.setdefault("supports", [])
        rows.append(rec)
        have_t.add(t)
        if doi:
            have_d.add(doi)
        added += 1
    save(d, rows)
    return added, skipped


def cmd_init(d: Path) -> None:
    p = store_path(d)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text("", encoding="utf-8")
    (d / "refs" / "README.md").write_text(
        "# 文献库\n\n"
        "`refs.jsonl` 一行一条；编号顺序即正文引用顺序。\n"
        "知网/万方导出 GB/T 7714 文本粘到 `refs/inbox.txt`，再跑：\n\n"
        "    py tools/ref_store.py import-gbt --dir <项目> --file refs/inbox.txt\n\n"
        "人工导入的 `status=manual`，机器核验的 `status=verified`，"
        "批量候选 `status=candidate`，三者不要混。\n",
        encoding="utf-8")
    print(f"ok {p}")


def cmd_import(d: Path, file: str, kind: str, status: str) -> None:
    text = Path(file).read_text(encoding="utf-8")
    if kind == "bib":
        recs = parse_bib(text)
    elif kind == "ris":
        recs = parse_ris(text)
    else:
        recs = [r for r in (parse_gbt(line) for line in text.splitlines()) if r]
    added, skipped = _add_many(d, recs, status)
    print(f"imported {added}，skipped {skipped}")


def cmd_add(d: Path, args: argparse.Namespace) -> None:
    rec = {
        "title": args.title,
        "authors": [a.strip() for a in args.authors.split(",") if a.strip()],
        "year": args.year,
        "venue": args.venue,
        "type": args.type,
        "doi": args.doi,
        "arxiv": args.arxiv,
        "url": args.url,
        "status": args.status,
        "provenance": {"verified_by": args.verified_by,
                       "verified_at": datetime.date.today().isoformat()},
        "supports": [],
    }
    added, _ = _add_many(d, [rec], args.status)
    print("added" if added else "skipped（重复）")


def cmd_list(d: Path) -> None:
    rows = load(d)
    if not rows:
        print("（空）")
        return
    print("| id | 年 | 类型 | 状态 | 题名 |")
    print("|---|---|---|---|---|")
    for r in rows:
        print(f"| {r.get('id')} | {r.get('year')} | {r.get('type')} | {r.get('status')} | {r.get('title')[:50]} |")


def extract_section(ms: str, title: str) -> str | None:
    m = re.search(r"(?m)^##\s+" + re.escape(title) + r"\s*$", ms)
    if not m:
        return None
    start = m.end()
    nxt = re.search(r"(?m)^##\s+", ms[start:])
    return ms[start:start + nxt.start()] if nxt else ms[start:]


def expand_group(g: str) -> list[int]:
    out: list[int] = []
    for part in g.split(","):
        part = part.strip()
        m = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if 0 < b - a <= 50:
                out.extend(range(a, b + 1))
        elif part.isdigit():
            out.append(int(part))
    return out


def compress(nums: list[int]) -> str:
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        if j - i >= 2:
            out.append(f"{nums[i]}-{nums[j]}")
        else:
            out.extend(str(x) for x in nums[i:j + 1])
        i = j + 1
    return ",".join(out)


# ---------------------------------------------------------------- 检查

def check(rows: list[dict], ms: str, cfg: dict) -> dict:
    refs, body = split_refs(ms)
    nums = cited_numbers(body)

    fails, warns = [], []
    if not rows:
        fails.append("文献库为空")
    if len(refs) != len(rows):
        fails.append(f"文末条目 {len(refs)} 条，文献库 {len(rows)} 条，数量不一致")

    for n, (_, entry) in enumerate(refs, 1):
        if n > len(rows):
            break
        rec = rows[n - 1]
        sim = overlap(entry, rec.get("title", ""))
        if sim < 0.5:
            fails.append(f"[{n}] 与文献库 {rec.get('id')} 题名相似度 {sim:.2f}，可能错位")
        if rec.get("status") == "retracted":
            fails.append(f"[{n}] {rec.get('id')} 已撤回")
        elif rec.get("status") == "candidate":
            warns.append(f"[{n}] {rec.get('id')} 仍是候选，未核验")
        elif rec.get("status") == "weak":
            warns.append(f"[{n}] {rec.get('id')} 仅弱匹配，须人工确认")

    cited = set(nums)
    for n in sorted(cited):
        if n > len(rows):
            fails.append(f"正文引用了 [{n}]，文献库没有对应条目")
    for i, rec in enumerate(rows, 1):
        if i not in cited:
            warns.append(f"{rec.get('id')} 列而未引")
        elif not rec.get("supports"):
            warns.append(f"{rec.get('id')} 已引用但没有支撑句记录")

    # 槽位覆盖
    slots = cfg.get("citation_slots", {}) or {}
    for title, specs in slots.items():
        text = extract_section(ms, title)
        if text is None:
            warns.append(f"槽位配置了“{title}”，但正文没有这一节")
            continue
        sec_nums = set(cited_numbers(text))
        sec_refs = [rows[n - 1] for n in sorted(sec_nums) if 1 <= n <= len(rows)]
        for spec in specs:
            intent = spec.get("intent")
            need = int(spec.get("min", 1))
            got = sum(1 for r in sec_refs
                      if any(s.get("intent") == intent for s in r.get("supports", [])))
            if got < need:
                fails.append(f"{title}：槽位 {intent} 需 {need} 条，实际 {got} 条")

    return {"fails": fails, "warns": warns, "n_rows": len(rows),
            "n_refs": len(refs), "n_cited": len(cited),
            "n_manual": sum(1 for r in rows if r.get("status") == "manual"),
            "n_candidate": sum(1 for r in rows if r.get("status") == "candidate")}


def render_md(r: dict) -> str:
    lines = ["## 13 文献库", "",
             f"- 记录 {r['n_rows']} 条；人工导入 {r['n_manual']} 条；候选 {r['n_candidate']} 条",
             f"- 文末条目 {r['n_refs']} 条；正文引用 {r['n_cited']} 处"]
    if r["fails"]:
        lines.append("- 未通过：" + "；".join(r["fails"]))
    if r["warns"]:
        lines.append("- 提示：" + "；".join(r["warns"]))
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- 重编号

def renumber(ms: str) -> tuple[str, dict[int, int], list[dict]]:
    m = re.search(r"(?m)^##\s*参考文献\s*$", ms)
    if not m:
        raise SystemExit("找不到“## 参考文献”")
    body, tail = ms[:m.start()], ms[m.end():]
    entries = {int(x.group(1)): x.group(2).strip() for x in REF_ENTRY.finditer(tail)}
    if not entries:
        raise SystemExit("参考文献一节没有可解析的条目")

    mapping: dict[int, int] = {}

    def repl(mt: re.Match) -> str:
        news = []
        for old in expand_group(mt.group(1)):
            if old not in entries:
                raise SystemExit(f"正文引用了 [{old}]，文末没有这一条")
            if old not in mapping:
                mapping[old] = len(mapping) + 1
            news.append(mapping[old])
        return "[" + compress(news) + "]"

    new_body = CITE.sub(repl, body)
    for old in entries:
        if old not in mapping:
            mapping[old] = len(mapping) + 1

    out = ["# 重编号结果", "", f"- 重排 {len(mapping)} 条"]
    new_refs = []
    for old, new in sorted(mapping.items(), key=lambda x: x[1]):
        new_refs.append(f"[{new}] {entries[old]}")
        if old != new:
            out.append(f"- [{old}] → [{new}]")
    new_ms = new_body + "## 参考文献\n\n" + "\n\n".join(new_refs) + "\n"
    return new_ms, mapping, [{"old": o, "new": n} for o, n in mapping.items()]


def cmd_export(d: Path, out: str, apply: bool) -> None:
    ms_path = d / "manuscript.md"
    if not ms_path.exists():
        raise SystemExit("缺少 manuscript.md")
    new_ms, mapping, _ = renumber(ms_path.read_text(encoding="utf-8"))

    target = Path(out) if out else (d / "manuscript.renumbered.md")
    target.write_text(new_ms, encoding="utf-8")

    if apply:
        ms_path.write_text(new_ms, encoding="utf-8")
        rows = load(d)
        by_new = sorted(mapping.items(), key=lambda x: x[1])
        reordered = [rows[o - 1] for o, _ in by_new if 1 <= o <= len(rows)]
        reordered += [r for i, r in enumerate(rows, 1) if i not in mapping]
        save(d, reordered)

    changed = sum(1 for o, n in mapping.items() if o != n)
    print(f"written {target}；{len(mapping)} 条，{changed} 条编号变化"
          + ("；已回写 manuscript.md 与 refs.jsonl" if apply else ""))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.add_argument("--dir", required=True)

    for name in ("import-gbt", "import-bib", "import-ris"):
        p = sub.add_parser(name)
        p.add_argument("--dir", required=True)
        p.add_argument("--file", required=True)
        p.add_argument("--status", default="manual" if name == "import-gbt" else "candidate",
                       choices=sorted(STATUS))

    p = sub.add_parser("add")
    p.add_argument("--dir", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--authors", default="")
    p.add_argument("--year", type=int, default=None)
    p.add_argument("--venue", default="")
    p.add_argument("--type", default="journal", choices=sorted(TYPES))
    p.add_argument("--doi", default="")
    p.add_argument("--arxiv", default="")
    p.add_argument("--url", default="")
    p.add_argument("--status", default="verified", choices=sorted(STATUS))
    p.add_argument("--verified-by", default="openalex")

    p = sub.add_parser("list")
    p.add_argument("--dir", required=True)

    p = sub.add_parser("check")
    p.add_argument("--dir", required=True)

    p = sub.add_parser("export")
    p.add_argument("--dir", required=True)
    p.add_argument("--out", default="")
    p.add_argument("--apply", action="store_true")

    args = ap.parse_args()
    d = Path(args.dir)
    if args.cmd == "init":
        cmd_init(d)
    elif args.cmd == "import-gbt":
        cmd_import(d, args.file, "gbt", args.status)
    elif args.cmd == "import-bib":
        cmd_import(d, args.file, "bib", args.status)
    elif args.cmd == "import-ris":
        cmd_import(d, args.file, "ris", args.status)
    elif args.cmd == "add":
        cmd_add(d, args)
    elif args.cmd == "list":
        cmd_list(d)
    elif args.cmd == "check":
        cfg = {}
        if (d / "project.json").exists():
            cfg = json.loads((d / "project.json").read_text(encoding="utf-8"))
        ms = (d / "manuscript.md").read_text(encoding="utf-8")
        r = check(load(d), ms, cfg)
        md = render_md(r)
        out = d / "checks" / "refs_report.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("# 文献库检查\n\n" + md, encoding="utf-8")
        print(md)
        sys.exit(0 if not r["fails"] else 1)
    else:
        cmd_export(d, args.out, args.apply)


if __name__ == "__main__":
    main()
