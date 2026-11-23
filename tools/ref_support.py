"""支撑句抽取：为一条文献找到能支持某句话的原文 span。

用法：
  py tools/ref_support.py add --dir projects/x --ref R-0001 --claim C-02 \
      --intent support --show
  py tools/ref_support.py add --dir projects/x --ref R-0001 --claim C-02 \
      --sentence "原文里的这一句"        # 人工指定，跳过抓取
  py tools/ref_support.py scan --dir projects/x --ref R-0001

取文顺序：arXiv 摘要 → Crossref 摘要 → 记录里的 url 正文 → 人工指定。
只取摘要与公开页面，不碰付费墙。

为什么要这一步：ref_audit 只证明"这篇论文存在"，支撑句才证明"这句话有依据"。
见 docs/17-证据库与引用流水线.md。
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from ref_store import load as load_refs, save as save_refs  # noqa: E402

INTENTS = {"background", "support", "contrast", "method_origin", "data_source", "limitation"}


def http(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "paperkit-refsupport/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def clean(text: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def from_arxiv(aid: str) -> str:
    raw = http("http://export.arxiv.org/api/query?id_list=" + urllib.parse.quote(aid) + "&max_results=1")
    m = re.search(r"(?s)<summary>(.*?)</summary>", raw)
    return clean(m.group(1)) if m else ""


def from_doi(doi: str) -> str:
    raw = http("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe=""))
    data = json.loads(raw)
    return clean(data.get("message", {}).get("abstract", "") or "")


def from_url(url: str) -> str:
    if not url.startswith("http"):
        return ""
    return clean(http(url))[:30000]


def fetch_text(rec: dict) -> tuple[str, str]:
    if rec.get("arxiv"):
        try:
            t = from_arxiv(rec["arxiv"])
            if t:
                return t, "arxiv_abstract"
        except Exception:  # noqa: BLE001
            pass
    if rec.get("doi"):
        try:
            t = from_doi(rec["doi"])
            if t:
                return t, "crossref_abstract"
        except Exception:  # noqa: BLE001
            pass
    if rec.get("url"):
        try:
            t = from_url(rec["url"])
            if t:
                return t, "url_text"
        except Exception:  # noqa: BLE001
            pass
    return "", "none"


def tokens(s: str) -> set[str]:
    s = s.lower()
    out = set(re.findall(r"[a-z]{3,}", s))
    cjk = re.sub(r"[^\u4e00-\u9fff]", "", s)
    out |= {cjk[i:i + 2] for i in range(len(cjk) - 1)}
    return out


def dice(a: str, b: str) -> float:
    x, y = tokens(a), tokens(b)
    if not x or not y:
        return 0.0
    return 2 * len(x & y) / (len(x) + len(y))


def split_sents(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。！？])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) >= 25]


def rank(text: str, claim: str) -> list[tuple[float, str]]:
    scored = [(dice(claim, s), s) for s in split_sents(text)]
    scored.sort(key=lambda x: -x[0])
    return scored


def cmd_add(d: Path, args: argparse.Namespace) -> None:
    rows = load_refs(d)
    rec = next((r for r in rows if r.get("id") == args.ref), None)
    if not rec:
        raise SystemExit(f"文献库里没有 {args.ref}")
    if args.intent not in INTENTS:
        raise SystemExit(f"intent 必须是 {sorted(INTENTS)}")

    if args.sentence:
        span, source, score = args.sentence, "manual", 1.0
    else:
        text, source = fetch_text(rec)
        if not text:
            raise SystemExit(f"{args.ref} 取不到摘要或正文，请用 --sentence 人工指定")
        ranked = rank(text, args.claim)
        if not ranked:
            raise SystemExit("没有可用的候选句")
        if args.show:
            print("候选项：")
            for s, sent in ranked[:3]:
                print(f"  {s:.2f}  {sent[:160]}")
        score, span = ranked[0]
        if score < args.min_score:
            print(f"警告：最高分 {score:.2f} 低于阈值 {args.min_score}，这条支撑可能不成立")

    supports = [s for s in rec.get("supports", [])
                if not (s.get("claim") == args.claim and s.get("intent") == args.intent)]
    supports.append({"claim": args.claim, "span": span, "intent": args.intent,
                     "score": round(float(score), 2), "source": source,
                     "added": date.today().isoformat()})
    rec["supports"] = supports
    save_refs(d, rows)
    print(f"{args.ref} <- {args.intent}: {span[:120]}")


def cmd_scan(d: Path, ref_id: str) -> None:
    rows = load_refs(d)
    rec = next((r for r in rows if r.get("id") == ref_id), None)
    if not rec:
        raise SystemExit(f"没有 {ref_id}")
    text, source = fetch_text(rec)
    if not text:
        print("取不到文本")
        return
    print(f"来源：{source}，长度 {len(text)}")
    for i, sent in enumerate(split_sents(text)[:20], 1):
        print(f"{i:02d}. {sent[:180]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add")
    p.add_argument("--dir", required=True)
    p.add_argument("--ref", required=True)
    p.add_argument("--claim", required=True)
    p.add_argument("--intent", default="support")
    p.add_argument("--sentence", default="")
    p.add_argument("--show", action="store_true")
    p.add_argument("--min-score", type=float, default=0.12)

    p = sub.add_parser("scan")
    p.add_argument("--dir", required=True)
    p.add_argument("--ref", required=True)

    args = ap.parse_args()
    d = Path(args.dir)
    if args.cmd == "add":
        cmd_add(d, args)
    else:
        cmd_scan(d, args.ref)


if __name__ == "__main__":
    main()
