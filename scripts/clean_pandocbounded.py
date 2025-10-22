from __future__ import annotations
import re
from pathlib import Path
import sys


def clean_file(p: Path) -> bool:
    s = p.read_text(encoding="utf-8", errors="strict")
    new_s = re.sub(r"\\pandocbounded\{([\s\S]*?)\}", r"\1", s)
    if new_s != s:
        p.write_text(new_s, encoding="utf-8")
        return True
    return False


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: clean_pandocbounded.py <tex-file>")
        return 2
    tex = Path(sys.argv[1])
    if not tex.exists():
        print(f"not found: {tex}")
        return 1
    changed = clean_file(tex)
    print("cleaned" if changed else "nochange")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

