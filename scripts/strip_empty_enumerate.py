from __future__ import annotations
import re
from pathlib import Path
import sys


PAT = re.compile(
    r"\\begin\{enumerate\}\s*"
    r"(?:\\def\\labelenumi\{[^}]*\}\s*)?"
    r"(?:\\setcounter\{enumi\}\{\d+\}\s*)?"
    r"(?:\\tightlist\s*)?"
    r"\\item\s*"
    r"\\end\{enumerate\}",
    re.MULTILINE,
)


def strip(tex: str) -> str:
    return PAT.sub("", tex)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: strip_empty_enumerate.py <tex-file>")
        return 2
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"not found: {p}")
        return 1
    s = p.read_text(encoding="utf-8", errors="strict")
    t = strip(s)
    if t != s:
        p.write_text(t, encoding="utf-8")
        print("[ok] stripped empty enumerate blocks")
    else:
        print("[info] no empty enumerate found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

