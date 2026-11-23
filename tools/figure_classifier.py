"""图表结构分类器：TF-IDF 质心，纯 Python，无第三方依赖。

用法：
  py tools/figure_classifier.py cv
  py tools/figure_classifier.py train
  py tools/figure_classifier.py predict --caption "Figure 3 Global map of ..."

训练数据：corpus/figures/corpus/labels.csv（人工标注）+ manifest.jsonl（图注）
模型输出：paperkit/figures/figure_classifier.json

五组：空间 / 统计 / 时序 / 结构 / 定性。
单标签对复合图有天然局限，预测结果附 margin，margin 小的人工复核。
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus" / "figures" / "corpus"
MODEL = ROOT / "paperkit" / "figures" / "figure_classifier.json"

GROUPS = {
    "map": "空间", "profile": "空间",
    "distribution": "统计", "scatter": "统计", "evaluation": "统计",
    "comparison": "统计", "heatmap": "统计",
    "timeseries": "时序",
    "architecture": "结构",
    "qualitative": "定性",
    "other": "其他",   # 当前语料里的 other 主要是配置文件文本截图
}


def toks(cap: str) -> list[str]:
    return re.findall(r"[a-z][a-z\-]{2,}", cap.lower())


def caption_title(cap: str) -> str:
    """取图注的第一句当图名，去掉 Figure N 前缀和面板描述。"""
    s = re.sub(r"^\s*(Figure|Fig\.?)\s*\d+\s*[:.]?\s*", "", cap)
    s = re.split(r"(?<=[.!?])\s", s)[0]
    s = re.split(r"\s*\([a-zA-Z]\)", s)[0]
    return s.strip() or cap[:120]


def weighted(cap: str) -> str:
    """图名重复两次 + 完整图注：图名信号加权，面板描述保留作补充。"""
    t = caption_title(cap)
    return f"{t} {t} {cap}"


def load() -> tuple[list[str], list[str]]:
    man = {}
    for line in (CORPUS / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            man.setdefault(r["file"], r)
    docs, ys, seen = [], [], set()
    for path in (CORPUS / "labels.csv", CORPUS / "labels_arxiv.csv"):
        if not path.exists():
            continue
        for r in csv.DictReader(path.open(encoding="utf-8-sig")):
            lab = r["label"].strip()
            if not lab or r["file"] in seen:
                continue
            cap = man.get(r["file"], {}).get("caption", "")
            if cap:
                seen.add(r["file"])
                docs.append(cap)
                ys.append(GROUPS.get(lab, "其他"))
    return docs, ys


def fit(docs: list[str], ys: list[str]) -> dict:
    df = collections.Counter()
    for d in docs:
        df.update(set(toks(weighted(d))))
    n = len(docs)
    idf = {w: math.log((1 + n) / (1 + c)) + 1 for w, c in df.items()}

    def vec(d: str) -> dict[str, float]:
        tf = collections.Counter(toks(weighted(d)))
        v = {w: (1 + math.log(c)) * idf.get(w, 1) for w, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1
        return {w: x / norm for w, x in v.items()}

    cent: dict[str, dict[str, float]] = {}
    for d, y in zip(docs, ys):
        c = cent.setdefault(y, {})
        for w, x in vec(d).items():
            c[w] = c.get(w, 0) + x
    for c in cent:
        norm = math.sqrt(sum(x * x for x in cent[c].values())) or 1
        cent[c] = {w: x / norm for w, x in cent[c].items()}
    return {"idf": idf, "centroids": cent, "n": n}


def predict(model: dict, caption: str) -> tuple[str, float, float]:
    tf = collections.Counter(toks(weighted(caption)))
    v = {w: (1 + math.log(c)) * model["idf"].get(w, 1) for w, c in tf.items()}
    norm = math.sqrt(sum(x * x for x in v.values())) or 1
    v = {w: x / norm for w, x in v.items()}
    scores = {c: sum(x * cent.get(w, 0) for w, x in v.items())
              for c, cent in model["centroids"].items()}
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    (g1, s1), (g2, s2) = ranked[0], ranked[1] if len(ranked) > 1 else (ranked[0], ("", 0))
    return g1, s1, s1 - s2


def cv(model: dict, docs: list[str], ys: list[str]) -> float:
    ok = 0
    conf = collections.defaultdict(collections.Counter)
    for i, (d, y) in enumerate(zip(docs, ys)):
        sub = fit(docs[:i] + docs[i + 1:], ys[:i] + ys[i + 1:])
        g, _, _ = predict(sub, d)
        conf[g][y] += 1
        if g == y:
            ok += 1
    print(f"留一法准确率 {ok/len(docs):.0%}（n={len(docs)}，多数类基线 "
          f"{max(collections.Counter(ys).values())/len(ys):.0%}）")
    print("混淆（行=预测，列=人工）：")
    labels = sorted(set(ys))
    print("pred\\true", *labels, sep="\t")
    for g in sorted(conf):
        print(g, *[conf[g][l] for l in labels], sep="\t")
    return ok / len(docs)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("cv")
    sub.add_parser("train")
    p = sub.add_parser("predict")
    p.add_argument("--caption", required=True)
    args = ap.parse_args()

    docs, ys = load()
    if args.cmd == "predict":
        model = json.loads(MODEL.read_text(encoding="utf-8"))
        g, s, m = predict(model, args.caption)
        print(f"{g}  相似度 {s:.2f}  领先 {m:.2f}" + ("  （建议人工复核）" if m < 0.05 else ""))
        return

    model = fit(docs, ys)
    if args.cmd == "cv":
        cv(model, docs, ys)
    else:
        acc = cv(model, docs, ys)
        model["groups"] = GROUPS
        model["cv_accuracy"] = round(acc, 3)
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        MODEL.write_text(json.dumps(model, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"written {MODEL}")


if __name__ == "__main__":
    main()
