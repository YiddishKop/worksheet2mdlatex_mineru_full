from __future__ import annotations
import re
from pathlib import Path
import sys


def replace_math_delimiters(tex: str) -> str:
    # Replace \( ... \) with $ ... $
    tex = re.sub(r"\\\(", "$", tex)
    tex = re.sub(r"\\\)", "$", tex)
    # Replace \[ ... \] with $$ ... $$
    tex = re.sub(r"\\\[", "$$", tex)
    tex = re.sub(r"\\\]", "$$", tex)
    return tex


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: fix_math_delimiters.py <tex-file>")
        return 2
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"not found: {p}")
        return 1
    src = p.read_text(encoding="utf-8", errors="strict")
    dst = replace_math_delimiters(src)
    if dst != src:
        p.write_text(dst, encoding="utf-8")
        print("[ok] replaced \\(, \\) and \\[ , \\] to $/$$")
    else:
        print("[info] no changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

