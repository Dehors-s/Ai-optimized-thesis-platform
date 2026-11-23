"""逐节语体测量：把一篇 md 按二级标题切开，对照画像给出偏差。

用途：成品往往不在项目目录里，`check_project` 跑不到；用这个脚本先看
每一节离目标画像有多远，再决定要不要重写。

用法：
  py tools/section_metrics.py --text outputs/双高论文_v3_四方向_全文.md
  py tools/section_metrics.py --text outputs/xxx.md --profiles rs_method,rs_results
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "corpus" / "profiles"
sys.path.insert(0, str(ROOT / "tools"))
from style_check import metrics  # noqa: E402

DEFAULT = ["rs_method", "rs_results", "rs_discussion"]


def split_sections(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"(?m)^##\s+", text)
    out = []
    for p in parts[1:]:
        lines = p.splitlines()
        title = lines[0].strip()
        body = "\n".join(lines[1:])
        if len(re.findall(r"[\u4e00-\u9fff]", body)) >= 200:
            out.append((title, body))
    return out


def load(p: str) -> dict:
    return json.loads((PROFILES / f"{p}.json").read_text(encoding="utf-8"))


def fails(m: dict, prof: dict) -> list[str]:
    out = []
    if abs(m["sent_mean"] - prof["sentence"]["mean"]) > prof["soft_rules"]["sentence_mean_tolerance"]:
        out.append("句均长")
    if abs(m["commas_per_sent"] - prof["commas_per_sentence"]) > prof["hard_rules"]["comma_tolerance"]:
        out.append("逗号/句")
    if abs(m["de_per_100_zh"] - prof["de_per_100_zh"]) > prof["hard_rules"]["de_tolerance"]:
        out.append("的/百字")
    if abs(m["gt80"] - prof["sentence"]["gt80"]) > prof["soft_rules"]["gt80_tolerance"]:
        out.append(">80字句")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--profiles", default=",".join(DEFAULT))
    args = ap.parse_args()

    text = Path(args.text).read_text(encoding="utf-8")
    profs = {p: load(p) for p in args.profiles.split(",") if p}
    secs = split_sections(text)
    if not secs:
        raise SystemExit("没有找到 >=200 汉字的二级小节")

    print(f"# {Path(args.text).name}")
    print()
    def guess(title: str) -> str | None:
        if "讨论" in title and "rs_discussion" in profs:
            return "rs_discussion"
        if ("实验" in title or "结果" in title) and "rs_results" in profs:
            return "rs_results"
        if "rs_method" in profs:
            return "rs_method"
        return None

    print("| 节 | 汉字 | 句均长 | 逗号/句 | 的/百字 | >80字句 | 对照画像 | 未通过 |")
    print("|---|---|---|---|---|---|---|---|")
    total = 0
    for title, body in secs:
        m = metrics(body)
        best = guess(title)
        if best is None:
            best, best_f = None, None
            for p, prof in profs.items():
                f = fails(m, prof)
                if best_f is None or len(f) < len(best_f):
                    best, best_f = p, f
        else:
            best_f = fails(m, profs[best])
        total += len(best_f or [])
        print(f"| {title} | {m['chars_zh']} | {m['sent_mean']} | {m['commas_per_sent']} | "
              f"{m['de_per_100_zh']} | {m['gt80']:.0%} | {best} | {'、'.join(best_f) or '—'} |")
    print()
    for p, prof in profs.items():
        print(f"- `{p}` 目标：句均长 {prof['sentence']['mean']}±{prof['soft_rules']['sentence_mean_tolerance']}，"
              f"逗号 {prof['commas_per_sentence']}±{prof['hard_rules']['comma_tolerance']}，"
              f"的/百字 {prof['de_per_100_zh']}±{prof['hard_rules']['de_tolerance']}")
    print(f"\n合计未通过项：{total}")
    sys.exit(0 if total == 0 else 1)


if __name__ == "__main__":
    main()
