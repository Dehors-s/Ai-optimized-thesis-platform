"""paperkit v1：论文项目的统一入口。

用法：
  py tools/paperkit.py new --name "某遥感论文" --dir projects/xxx --title "题目"
  py tools/paperkit.py check --dir projects/xxx
  py tools/paperkit.py terms --text outputs/xxx.md
  py tools/paperkit.py profiles
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def run(script: str, args: list[str]) -> int:
    cmd = [sys.executable, str(TOOLS / script), *args]
    return subprocess.run(cmd, cwd=ROOT).returncode


def main() -> None:
    ap = argparse.ArgumentParser(prog="paperkit", description="论文项目脚手架与检查")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="新建论文项目")
    p_new.add_argument("--name", required=True)
    p_new.add_argument("--dir", required=True)
    p_new.add_argument("--title", default="论文题目（待定）")
    p_new.add_argument("--type", default="empirical",
                       choices=["empirical", "engineering", "survey", "systems", "theory"])
    p_new.add_argument("--mode", default="project", choices=["template", "project"])
    p_new.add_argument("--journal", default="")
    p_new.add_argument("--language", default="zh", choices=["zh", "en"])
    p_new.add_argument("--discipline", default="")

    p_check = sub.add_parser("check", help="检查论文项目")
    p_check.add_argument("--dir", required=True)

    p_terms = sub.add_parser("terms", help="术语体检")
    p_terms.add_argument("--text", required=True)
    p_terms.add_argument("--out", default="")

    p_audit = sub.add_parser("audit", help="引用与修辞审计（可对任意 md）")
    p_audit.add_argument("--text", required=True)
    p_audit.add_argument("--online", action="store_true", help="逐条联网核验文献")

    sub.add_parser("profiles", help="重建全部语体画像")

    args = ap.parse_args()
    if args.cmd == "new":
        code = run("new_project.py", ["--name", args.name, "--dir", args.dir,
                                      "--title", args.title, "--type", args.type,
                                      "--mode", args.mode,
                                      "--journal", args.journal, "--language", args.language,
                                      "--discipline", args.discipline])
    elif args.cmd == "check":
        code = run("check_project.py", ["--dir", args.dir])
    elif args.cmd == "terms":
        extra = ["--text", args.text] + (["--out", args.out] if args.out else [])
        code = run("term_check.py", extra)
    elif args.cmd == "audit":
        extra = ["--text", args.text] + (["--online"] if args.online else [])
        code = run("ref_audit.py", extra)
        code |= run("rhetoric_check.py", ["--text", args.text])
    else:
        code = run("build_profiles.py", [])
        code |= run("build_section_profiles.py", [])
    sys.exit(code)


if __name__ == "__main__":
    main()
