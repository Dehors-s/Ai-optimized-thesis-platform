"""检查论文项目：结构、摘要、分节、术语、数字、规则、主张。

用法：py tools/check_project.py --dir projects/xxx
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from style_check import metrics  # noqa: E402
from term_check import TERMS  # noqa: E402
from ref_audit import audit as ref_audit_fn, render_md as ref_md  # noqa: E402
from rhetoric_check import check as rhet_check, render_md as rhet_md  # noqa: E402
from evidence_store import load as ev_load, check as ev_check, render_md as ev_md  # noqa: E402
from ref_store import load as rf_load, check as rf_check, render_md as rf_md  # noqa: E402
from number_check import check as num_check, render_md as num_md  # noqa: E402

PROFILES = ROOT / "corpus" / "profiles"


def score_text(text: str, profile: dict) -> tuple[int, list[dict]]:
    m = metrics(text)
    rows, score = [], 100.0

    def add(name, value, target, ok, warn=False):
        nonlocal score
        if not ok:
            score -= 20
        elif warn:
            score -= 4
        rows.append({"item": name, "value": value, "target": target,
                     "status": "pass" if ok and not warn else ("warn" if warn else "fail")})

    for key, limit, label in [("dashes", 0, "破折号"), ("quotes", profile["hard_rules"]["max_quote"], "引号")]:
        add(label, m[key], f"≤{limit}", m[key] <= limit)

    hits = [b for b in profile["hard_rules"].get("meta_blacklist", []) if b in text]
    add("元话语", "、".join(hits) or 0, "0", not hits)

    for key, target, tol, label in [
        ("commas_per_sent", profile["commas_per_sentence"], profile["hard_rules"]["comma_tolerance"], "逗号/句"),
        ("de_per_100_zh", profile["de_per_100_zh"], profile["hard_rules"]["de_tolerance"], "的/百汉字"),
    ]:
        dev = abs(m[key] - target)
        add(label, m[key], f"{target}±{tol}", dev <= tol, warn=tol * 0.6 < dev <= tol)

    for key, target, tol, label in [
        ("sent_mean", profile["sentence"]["mean"], profile["soft_rules"]["sentence_mean_tolerance"], "句均长"),
        ("gt80", profile["sentence"]["gt80"], profile["soft_rules"]["gt80_tolerance"], ">80字句"),
    ]:
        dev = abs(m[key] - target)
        add(label, m[key], f"{target}±{tol}", dev <= tol, warn=tol < dev <= tol * 2)

    return max(0, round(score)), rows


def extract(ms: str, title: str) -> str | None:
    pat = re.compile(r"(?m)^##\s+" + re.escape(title) + r"\s*$")
    m = pat.search(ms)
    if not m:
        return None
    start = m.end()
    nxt = re.compile(r"(?m)^##\s+").search(ms, start)
    return ms[start:(nxt.start() if nxt else len(ms))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    args = ap.parse_args()
    d = Path(args.dir)
    lines = [f"# 项目检查报告：{d.name}", ""]
    ok_all = True

    cfg = {}
    if (d / "project.json").exists():
        cfg = json.loads((d / "project.json").read_text(encoding="utf-8"))
    ptype = cfg.get("paper_type", "未配置")
    mode = cfg.get("mode", "project")
    required = ["facts.md", "paper_ir.json", "outline.md", "manuscript.md"]
    if mode == "project":
        required.append("innovation.md")
    missing = [f for f in required if not (d / f).exists()]
    lines += ["## 1 结构", "",
              f"- 论文类型：{ptype}",
              f"- 入口模式：{mode}（template=素材少，仅结构参考；project=有数据，必须绑定创新点）",
              f"- 必需文件：{'齐全' if not missing else '缺失 ' + '、'.join(missing)}", ""]
    if mode == "template":
        lines += ["> 模板模式：未绑定项目数据与创新点，**不可作为投稿稿**。", ""]
    ok_all &= not missing

    if not missing:
        ms = (d / "manuscript.md").read_text(encoding="utf-8")
        profiles = cfg.get("profiles") or {}
        sections = cfg.get("sections", [])
        ev_path = d / "evidence" / "evidence.jsonl"
        ledger = ev_load(d) if ev_path.exists() and ev_path.stat().st_size > 0 else []
        use_ledger = any(r.get("type") == "number" and r.get("value") for r in ledger)

        # 摘要
        abs_title = next((s["title"] for s in sections if s.get("role") == "abstract"), "摘要")
        abs_text = extract(ms, abs_title)
        pname = profiles.get("abstract")
        if not abs_text or len(abs_text.strip()) < 50:
            lines += [f"## 2 摘要语体", "", f"- 未找到“{abs_title}”或内容过短", ""]
            ok_all = False
        elif not pname or not (PROFILES / f"{pname}.json").exists():
            lines += ["## 2 摘要语体", "", "- 未配置画像，跳过语体检查", ""]
        else:
            prof = json.loads((PROFILES / f"{pname}.json").read_text(encoding="utf-8"))
            sc, rows = score_text(abs_text, prof)
            lines += ["## 2 摘要语体", "", f"- 画像：`{pname}`", f"- 分数：**{sc}/100**", "",
                      "| 项 | 实际 | 目标 | 判定 |", "|---|---|---|---|"]
            lines += [f"| {r['item']} | {r['value']} | {r['target']} | {r['status']} |" for r in rows]
            lines += [""]
            ok_all &= sc >= 70

        # 分节
        lines += ["## 3 分节语体", ""]
        for s in sections:
            pname = s.get("profile")
            if not pname:
                continue
            text = extract(ms, s["title"])
            if not text or len(text.strip()) < 50:
                lines += [f"- {s['title']}（{pname}）：内容过短，跳过"]
                continue
            if not (PROFILES / f"{pname}.json").exists():
                lines += [f"- {s['title']}（{pname}）：画像不存在，跳过"]
                continue
            prof = json.loads((PROFILES / f"{pname}.json").read_text(encoding="utf-8"))
            sc, rows = score_text(text, prof)
            fails = [r["item"] for r in rows if r["status"] == "fail"]
            lines += [f"- {s['title']}（{pname}）：**{sc}/100**" + (f"，未通过：{'、'.join(fails)}" if fails else "")]
            ok_all &= sc >= 70
        lines += [""]

        # 术语
        terms = {k: ms.count(k) for k in TERMS if ms.count(k)}
        n = sum(terms.values())
        zh = len(re.findall(r"[\u4e00-\u9fff]", ms)) or 1
        lines += ["## 4 术语", "", f"- 造词命中：{n} 次，{n / zh * 1000:.1f} 次/千汉字", ""]
        if terms:
            lines += [f"- {k}：{v} 次" for k, v in terms.items()]
        ok_all &= n / zh * 1000 < 2

        # 数字溯源
        if use_ledger:
            lines += ["## 5 数字溯源", "", "- 已启用证据台账，逐值反查见第 14 节", ""]
        else:
            facts = (d / "facts.md").read_text(encoding="utf-8")
            nums = set(re.findall(r"\d+\.\d{2,4}|\d{4,}", ms))
            miss = sorted(x for x in nums if x not in facts)
            lines += ["## 5 数字溯源", "", f"- 正文数字 {len(nums)} 个，facts.md 中找不到 {len(miss)} 个", ""]
            if miss:
                lines += ["- 缺失：" + "、".join(miss[:15])]
            ok_all &= len(miss) <= len(nums) * 0.05

        # 规则
        rules = cfg.get("rules", {})
        forbid = rules.get("forbidden_phrases", ["优于", "高于对照", "纯自研", "证明了", "显著领先", "全面超越"])
        hits = [w for w in forbid if w in ms]
        lines += ["## 6 规则", ""]
        lines += [f"- 命中禁用表述：{'、'.join(hits)}" if hits else "- 未命中禁用表述"]
        if hits:
            ok_all = False
        attr = rules.get("required_attribution")
        if attr and attr.get("number") in ms and attr.get("keyword") not in ms:
            lines += [f"- 结果段缺少归属说明（{attr.get('keyword')}）"]
            ok_all = False
        for st in rules.get("required_statements", []):
            if st.get("if") in ms and st.get("then") not in ms:
                lines += [f"- 提到“{st['if']}”但未说明“{st['then']}”"]
                ok_all = False
        lines += [""]

        # 创新点
        lines += ["## 7 创新点", ""]
        if mode == "project":
            inv = (d / "innovation.md").read_text(encoding="utf-8")
            accepted = len(re.findall(r"作者决定[:：]\s*接受", inv))
            lines += [f"- 已接受创新点：{accepted} 条"]
            if accepted == 0:
                lines += ["- 未确认任何创新点（project 模式要求至少 1 条）"]
                ok_all = False
        else:
            lines += ["- 模板模式：不要求创新点"]
        lines += [""]

        # 主张
        ir = json.loads((d / "paper_ir.json").read_text(encoding="utf-8"))
        claims = ir.get("claims", [])
        lines += ["## 8 主张", "", f"- claims：{len(claims)} 条"]
        if not claims:
            lines += ["- 尚未填写 claims"]
            if mode == "project":
                ok_all = False
        lines += [""]

        # 引用
        ref = ref_audit_fn(ms)
        lines += [ref_md(ref)]
        ok_all &= not ref["fails"]

        # 修辞
        rt = rhet_check(ms)
        lines += [rhet_md(rt)]
        if rt["verdict"] == "fail":
            ok_all = False

        # 声明
        lines += ["## 11 声明", ""]

        def filled(title: str) -> bool:
            body = extract(ms, title) or ""
            body = re.sub(r"[（(][^）)]*[）)]", "", body)   # 去掉模板占位说明
            return len(re.findall(r"[\u4e00-\u9fff]", body)) >= 20

        ai_heads = ["AI 使用声明", "人工智能使用声明", "生成式人工智能使用声明"]
        hit = next((h for h in ai_heads if filled(h)), "")
        lines += [f"- AI 使用声明：{hit}" if hit else "- AI 使用声明：未写或只有占位"]
        avail_heads = ["数据与代码可用性", "数据可用性", "数据与代码"]
        avail = next((h for h in avail_heads if filled(h)), "")
        lines += [f"- 数据可用性：{avail}" if avail else "- 数据可用性：未写或只有占位"]
        if mode == "project" and not hit:
            lines += ["  - 多数期刊与 ICMJE 要求披露 AI 使用；请写明工具、环节、作者复核方式。"]
        if mode == "project" and not avail:
            lines += ["  - 建议写明数据与代码的获取方式或不可获取的原因。"]
        lines += [""]

        # 证据库
        if ledger:
            er = ev_check(ledger, ms, cfg)
            lines += [ev_md(er)]
            ok_all &= not er["fails"]
        else:
            lines += ["## 12 证据", "", "- 未建立证据库（`evidence/evidence.jsonl`）", ""]

        # 文献库
        rf_path = d / "refs" / "refs.jsonl"
        if rf_path.exists() and rf_path.stat().st_size > 0:
            rr = rf_check(rf_load(d), ms, cfg)
            lines += [rf_md(rr)]
            ok_all &= not rr["fails"]
        else:
            lines += ["## 13 文献库", "", "- 未建立文献库（`refs/refs.jsonl`）", ""]

        # 数字反查（台账模式）
        if use_ledger:
            nr = num_check(ledger, ms)
            lines += [num_md(nr)]
            ok_all &= not nr["fails"]

    verdict = "通过" if ok_all else "有未通过项"
    lines = [f"**结论：{verdict}**", ""] + lines
    out = d / "checks" / "report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"written {out} | {verdict}")


if __name__ == "__main__":
    main()
