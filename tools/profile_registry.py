"""画像解析：按「期刊 × 语言 × 学科」查注册表，找不到就退回语言默认。

用法（库）：from profile_registry import resolve
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "paperkit" / "profiles" / "registry.json"


def load() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def resolve(journal: str = "", language: str = "zh", discipline: str = "") -> dict | None:
    reg = load()
    for e in reg.get("entries", []):
        if e.get("journal") == journal and e.get("language") == language:
            if not discipline or e.get("discipline") == discipline:
                return dict(e["profiles"])
    for e in reg.get("entries", []):
        if e.get("journal") == journal and e.get("language") == language:
            return dict(e["profiles"])
    return reg.get("defaults", {}).get(language)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", default="")
    ap.add_argument("--language", default="zh")
    ap.add_argument("--discipline", default="")
    a = ap.parse_args()
    print(json.dumps(resolve(a.journal, a.language, a.discipline), ensure_ascii=False, indent=2))
