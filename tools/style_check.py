"""按语体画像检查一段中文摘要/正文，输出指标、判定与分数。

用法：
  py tools/style_check.py --text outputs/摘要_v5_遥感标定.md --profile rs_abstract
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "corpus" / "profiles"


def load_text(path: Path) -> str:
    t = path.read_text(encoding="utf-8")
    t = t.split("## 指标")[0]
    t = re.sub(r"(?m)^#.*$", "", t)
    return t.strip()


def normalize(t: str) -> str:
    t = re.sub(r"(?<=[^\d])\.\s+", "。", t)
    t = re.sub(r",\s+", "，", t)
    return t


def split_sents(t: str) -> list[str]:
    t = normalize(t)
    return [s.strip() for s in re.split(r"(?<=[。！？])", t) if len(s.strip()) >= 8]


def metrics(t: str) -> dict:
    ss = split_sents(t)
    lens = [len(s) for s in ss]
    zh = len(re.findall(r"[\u4e00-\u9fff]", t)) or 1
    de = sum(s.count("的") for s in ss)
    comma = sum(s.count("，") for s in ss)
    return {
        "chars_zh": len(re.findall(r"[\u4e00-\u9fff]", t)),
        "paragraphs": len([p for p in t.split("\n\n") if p.strip()]),
        "sentences": len(ss),
        "sent_mean": round(sum(lens) / len(lens), 1) if lens else 0,
        "sent_median": sorted(lens)[len(lens) // 2] if lens else 0,
        "gt80": round(sum(1 for x in lens if x > 80) / len(ss), 3) if ss else 0,
        "commas_per_sent": round(comma / len(ss), 2) if ss else 0,
        "de_per_100_zh": round(de / zh * 100, 2),
        "semicolons": t.count("；"),
        "dashes": t.count("——"),
        "quotes": t.count("“"),
        "meta_hits": [],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--profile", default="rs_abstract")
    args = ap.parse_args()

    prof = json.loads((PROFILES / f"{args.profile}.json").read_text(encoding="utf-8"))
    t = load_text(ROOT / args.text if not Path(args.text).is_absolute() else Path(args.text))
    m = metrics(t)
    for b in prof["hard_rules"].get("meta_blacklist", []):
        if b in t:
            m["meta_hits"].append(b)

    rows = []
    score = 100.0

    def check(name, value, target, status, note=""):
        rows.append({"metric": name, "value": value, "target": target, "status": status, "note": note})

    # 硬规则
    for key, limit, label in [("dashes", prof["hard_rules"]["max_dash"], "破折号"),
                              ("quotes", prof["hard_rules"]["max_quote"], "引号")]:
        v = m[key]
        ok = v <= limit
        if not ok:
            score -= 10
        check(label, v, f"≤{limit}", "pass" if ok else "fail")

    if m["meta_hits"]:
        score -= 20
        check("元话语", "、".join(m["meta_hits"]), "0", "fail")
    else:
        check("元话语", 0, "0", "pass")

    # 逗号
    target = prof["commas_per_sentence"]
    tol = prof["hard_rules"]["comma_tolerance"]
    dev = abs(m["commas_per_sent"] - target)
    if dev > tol:
        score -= min(20, dev / tol * 10)
        st = "fail"
    elif dev > tol * 0.6:
        score -= 4
        st = "warn"
    else:
        st = "pass"
    check("逗号/句", m["commas_per_sent"], f"{target}±{tol}", st)

    # 的密度
    target = prof["de_per_100_zh"]
    tol = prof["hard_rules"]["de_tolerance"]
    dev = abs(m["de_per_100_zh"] - target)
    if dev > tol:
        score -= min(20, dev / tol * 10)
        st = "fail"
    elif dev > tol * 0.6:
        score -= 4
        st = "warn"
    else:
        st = "pass"
    check("的/百汉字", m["de_per_100_zh"], f"{target}±{tol}", st)

    # 句长（软）
    target = prof["sentence"]["mean"]
    tol = prof["soft_rules"]["sentence_mean_tolerance"]
    dev = abs(m["sent_mean"] - target)
    if dev > tol:
        score -= min(15, (dev - tol) / tol * 10)
        st = "warn" if dev < tol * 2 else "fail"
    else:
        st = "pass"
    check("句均长", m["sent_mean"], f"{target}±{tol}", st)

    # >80 字句（软）
    target = prof["sentence"]["gt80"]
    tol = prof["soft_rules"]["gt80_tolerance"]
    dev = abs(m["gt80"] - target)
    if dev > tol:
        score -= min(15, (dev - tol) / tol * 10)
        st = "warn" if dev < tol * 2 else "fail"
    else:
        st = "pass"
    check(">80字句", f"{m['gt80']:.0%}", f"{target:.0%}±{tol:.0%}", st)

    score = max(0, round(score))
    grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D"
    out = {"profile": args.profile, "score": score, "grade": grade, "metrics": m, "checks": rows}
    print(json.dumps(out, ensure_ascii=False, indent=2))

    print(f"\n| 指标 | 实际 | 目标 | 判定 |")
    print("|---|---|---|---|")
    for r in rows:
        print(f"| {r['metric']} | {r['value']} | {r['target']} | {r['status']} |")
    print(f"\n**{score}/100（{grade}）**")


if __name__ == "__main__":
    main()
