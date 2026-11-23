"""参考文献审计：引用完整性、复用度、语种、时效，可选联网核验。

用法：
  py tools/ref_audit.py --text outputs/xxx.md
  py tools/ref_audit.py --text outputs/xxx.md --online
  py tools/ref_audit.py --text outputs/xxx.md --json

设计依据：
- Phantom References (arXiv:2607.00738)：幻觉引用能穿过顶会评审，
  单篇出现 >=2 条的比例约 5%；必须逐条核验，不能只看格式。
- ScientistOne (arXiv:2605.26340)：基线系统幻觉引用率最高 21%。
- Citing Less Critically (arXiv:2609.01432)：LLM 少批判、偏好高引老文。
- GB/T 7714-2015：中文期刊参考文献著录规则。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

CJK = re.compile(r"[\u4e00-\u9fff]")
YEAR = re.compile(r"(19|20)\d{2}")
DOI = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
ARXIV = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5})(v\d+)?", re.I)


def split_refs(text: str) -> tuple[list[tuple[int, str]], str]:
    """返回 [(编号, 条目), ...] 和去掉参考文献后的正文。"""
    m = re.search(r"(?m)^#{1,3}\s*参考文献\s*$", text)
    if not m:
        # 也接受“References”
        m = re.search(r"(?m)^#{1,3}\s*(?:References|REFERENCES)\s*$", text)
    if not m:
        return [], text
    body = text[: m.start()]
    tail = text[m.end():]
    refs: list[tuple[int, str]] = []
    cur: tuple[int, str] | None = None
    for line in tail.splitlines():
        s = line.strip()
        if not s:
            continue
        mm = re.match(r"^\[(\d+)\]\s*(.*)$", s)
        if mm:
            if cur:
                refs.append(cur)
            cur = (int(mm.group(1)), mm.group(2).strip())
        elif cur and not s.startswith("#"):
            cur = (cur[0], cur[1] + " " + s)
    if cur:
        refs.append(cur)
    return refs, body


def cited_numbers(body: str) -> list[int]:
    out: list[int] = []
    for m in re.finditer(r"\[(\d+(?:\s*[-,–]\s*\d+)*)\]", body):
        for part in re.split(r",", m.group(1)):
            part = part.strip()
            rng = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", part)
            if rng:
                a, b = int(rng.group(1)), int(rng.group(2))
                if 0 < b - a <= 50:
                    out.extend(range(a, b + 1))
            elif part.isdigit():
                out.append(int(part))
    return out


def http_ok(url: str, timeout: float = 8.0) -> tuple[bool, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "paperkit-refaudit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 300, str(r.status)
    except Exception as e:  # noqa: BLE001
        return False, type(e).__name__


def openalex_lookup(q: str, surname: str) -> tuple[int, float, str] | None:
    """OpenAlex 对机器学习会议论文覆盖比 Crossref 好，用作回退。"""
    url = "https://api.openalex.org/works?per-page=5&search=" + urllib.parse.quote(q[:200])
    req = urllib.request.Request(url, headers={"User-Agent": "paperkit-refaudit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:  # noqa: BLE001
        return None
    results = data.get("results") or []
    if not results:
        return None
    best = (0, 0.0, "")
    for it in results:
        t = it.get("title") or ""
        d = overlap(q, t)
        a = 0
        if surname:
            names = [((x.get("author") or {}).get("display_name") or "").lower()
                     for x in it.get("authorships", [])]
            a = int(any(surname in n for n in names))
        if (a, d) > best[:2]:
            best = (a, d, t)
    return best


def verify_online(entry: str) -> dict:
    """有标识符就查标识符；没有就用 Crossref 题录模糊检索。"""
    out = {"status": "unverified", "how": "", "detail": ""}
    m = DOI.search(entry)
    if m:
        ok, detail = http_ok("https://doi.org/api/handles/" + urllib.parse.quote(m.group(0), safe=""))
        out.update(status="ok" if ok else "fail", how="doi", detail=m.group(0) + " " + detail)
        return out
    m = ARXIV.search(entry)
    if m:
        ok, detail = http_ok("http://export.arxiv.org/api/query?id_list=" + m.group(1) + "&max_results=1")
        out.update(status="ok" if ok else "fail", how="arxiv", detail=m.group(1) + " " + detail)
        return out
    q = re.sub(r"^[^.]{0,160}?\.\s*", "", entry)          # 去掉作者段
    q = re.split(r"\[(?:C|J|M|D|R|S|N|P|EB/OL|DB/OL|J/OL)\]", q, maxsplit=1)[0]
    q = re.split(r"//", q, maxsplit=1)[0].strip(" .;:：，,")
    if len(q) < 10:
        return out
    surname = ""
    ma = re.match(r"^([A-Z][A-Za-z\-']{1,30})\s+[A-Z]", entry)
    if ma:
        surname = ma.group(1).lower()

    url = ("https://api.crossref.org/works?rows=5&select=title,DOI,author&query.bibliographic="
           + urllib.parse.quote(q[:200]))
    req = urllib.request.Request(url, headers={"User-Agent": "paperkit-refaudit/1.0 (mailto:none@example.com)"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8", "ignore"))
        items = data.get("message", {}).get("items", [])
        if not items:
            out.update(status="fail", how="crossref", detail="no match")
            return out

        def score(it: dict) -> tuple[int, float, str]:
            t = (it.get("title") or [""])[0]
            d = overlap(q, t)
            a = 0
            if surname:
                a = int(any((au.get("family") or "").lower() == surname
                            for au in it.get("author", [])))
            return a, d, t

        a, d, title = max((score(it) for it in items), key=lambda x: (x[0], x[1]))
        if d >= 0.6 and (not surname or a):
            out.update(status="ok", how="crossref",
                       detail=f"{title} | dice={d:.2f} | 作者{'匹配' if a else '未检'}")
            return out
        # Crossref 对 ML 会议论文覆盖差，回退 OpenAlex 再试一次
        oa = openalex_lookup(q, surname)
        if oa and oa[1] >= 0.6 and (not surname or oa[0]):
            out.update(status="ok", how="openalex",
                       detail=f"{oa[2]} | dice={oa[1]:.2f} | 作者{'匹配' if oa[0] else '未检'}")
            return out
        st = "weak" if max(d, oa[1] if oa else 0) >= 0.5 else "fail"
        out.update(status=st, how="crossref",
                   detail=f"{title} | dice={d:.2f} | 作者{'不匹配' if surname else '未检'}"
                          + (f"；OpenAlex: {oa[2]} dice={oa[1]:.2f}" if oa else "；OpenAlex 无结果"))
    except Exception as e:  # noqa: BLE001
        out.update(status="unverified", how="crossref", detail=type(e).__name__)
    return out


def tokens(s: str) -> set[str]:
    s = s.lower()
    out = set(re.findall(r"[a-z]{4,}", s))
    cjk = re.sub(r"[^\u4e00-\u9fff]", "", s)
    out |= {cjk[i:i + 2] for i in range(len(cjk) - 1)}
    return out


def overlap(q: str, title: str) -> float:
    """Dice 系数：双向都算，避免短标题被长条目带偏。"""
    a, b = tokens(q), tokens(title)
    if not a or not b:
        return 0.0
    return 2 * len(a & b) / (len(a) + len(b))


def audit(text: str, online: bool = False, recent_years: int = 5) -> dict:
    refs, body = split_refs(text)
    nums = cited_numbers(body)
    ref_ids = [n for n, _ in refs]
    dup_ids = sorted({n for n in ref_ids if ref_ids.count(n) > 1})

    counts: dict[int, int] = {n: 0 for n in ref_ids}
    for n in nums:
        if n in counts:
            counts[n] += 1

    cited = [n for n, c in counts.items() if c > 0]
    uncited = [n for n, c in counts.items() if c == 0]
    undefined = sorted({n for n in nums if n not in ref_ids})

    entry_text = " ".join(r for _, r in refs)
    years = [int(YEAR.search(r).group(0)) for _, r in refs if YEAR.search(r)]
    zh_refs = [n for n, r in refs if len(CJK.findall(r)) >= 4]
    cur = 2026
    recent = [y for y in years if y >= cur - recent_years]

    once = sum(1 for c in counts.values() if c == 1)
    multi = sum(1 for c in counts.values() if c > 1)
    total_cites = sum(counts.values())

    rows = {
        "n_refs": len(refs),
        "n_citations": total_cites,
        "cited_refs": len(cited),
        "uncited_refs": uncited,
        "undefined_citations": undefined,
        "duplicate_ids": dup_ids,
        "cited_once": once,
        "cited_multi": multi,
        "zh_refs": len(zh_refs),
        "zh_ratio": round(len(zh_refs) / len(refs), 3) if refs else 0.0,
        "recent_ratio": round(len(recent) / len(years), 3) if years else 0.0,
        "median_year": sorted(years)[len(years) // 2] if years else None,
        "no_year": len(refs) - len(years),
        "has_refs": bool(refs),
    }

    if online and refs:
        checks = []
        for n, r in refs:
            v = verify_online(r)
            v["id"] = n
            v["entry"] = r[:90]
            checks.append(v)
        rows["online"] = checks
        rows["online_fail"] = [c["id"] for c in checks if c["status"] in ("fail", "weak")]

    # 判定
    fails, warns = [], []
    if not refs:
        fails.append("没有参考文献")
    if undefined:
        fails.append(f"正文引用了不存在的条目：{undefined}")
    if uncited:
        warns.append(f"列而未引：{uncited}")
    if dup_ids:
        fails.append(f"编号重复：{dup_ids}")
    if refs and once == len(refs) and len(refs) >= 5:
        warns.append("所有条目都只被引用一次，像在凑引用")
    if refs and rows["zh_ratio"] == 0 and len(refs) >= 5:
        warns.append("没有中文文献")
    if years and rows["recent_ratio"] < 0.3:
        warns.append(f"近 {recent_years} 年文献占比 {rows['recent_ratio']:.0%}，偏低")
    if rows.get("online_fail"):
        fails.append(f"联网核验失败：{rows['online_fail']}")

    rows["fails"] = fails
    rows["warns"] = warns
    return rows


def render_md(r: dict) -> str:
    lines = ["## 9 参考文献", ""]
    if not r["has_refs"]:
        lines += ["- 未找到“参考文献”一节", ""]
        return "\n".join(lines)
    lines += [
        f"- 条目 {r['n_refs']} 条，正文引用 {r['n_citations']} 处，被引条目 {r['cited_refs']} 条",
        f"- 只被引一次：{r['cited_once']} 条；被引多次：{r['cited_multi']} 条",
        f"- 中文文献：{r['zh_refs']} 条（{r['zh_ratio']:.0%}）",
        f"- 近五年文献占比：{r['recent_ratio']:.0%}；年份中位数：{r['median_year']}",
    ]
    if r["undefined_citations"]:
        lines.append(f"- **引用了不存在的编号**：{r['undefined_citations']}")
    if r.get("online"):
        bad = [c for c in r["online"] if c["status"] != "ok"]
        lines.append(f"- 联网核验：{len(r['online']) - len(bad)}/{len(r['online'])} 通过")
        for c in bad[:10]:
            lines.append(f"  - [{c['id']}] {c['status']}（{c['how']}）：{c['detail']}")
    if r["fails"]:
        lines += ["- 未通过：" + "；".join(r["fails"])]
    if r["warns"]:
        lines += ["- 提示：" + "；".join(r["warns"])]
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--online", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    p = Path(args.text)
    text = p.read_text(encoding="utf-8")
    r = audit(text, online=args.online)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(render_md(r))
    sys.exit(0 if not r["fails"] else 1)


if __name__ == "__main__":
    main()
