from __future__ import annotations
import re
from pathlib import Path
import sys


def fix_tex(content: str) -> str:
    # Replace angle patterns globally (works both inside and outside math)
    out = content
    out = re.sub(r"∠\s*([A-Za-z]{1,6})", r"\\ensuremath{\\angle {\1}}", out)
    out = re.sub(r"△\s*([A-Za-z]{1,6})", r"\\ensuremath{\\triangle {\1}}", out)
    out = re.sub(r"([0-9]+(?:\.[0-9]+)?)\s*°", r"\\ensuremath{\1^{\\circ}}", out)
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: fix_angle_patterns_in_tex.py <tex-file>")
        return 2
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"not found: {p}")
        return 1
    src = p.read_text(encoding="utf-8", errors="strict")
    dst = fix_tex(src)
    if dst != src:
        p.write_text(dst, encoding="utf-8")
        print("[ok] patched angle/degree patterns in tex")
    else:
        print("[info] no changes applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

