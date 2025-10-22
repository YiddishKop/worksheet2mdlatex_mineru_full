from __future__ import annotations
import re
from pathlib import Path
import sys


_INLINE_MATH = re.compile(r"\$(?!\$)([^$]*?)\$")
_DISPLAY_MATH = re.compile(r"\$\$([\s\S]*?)\$\$")


def _fix_in_math(s: str) -> str:
    # Turn \\alpha, \\frac, \\angle, ... into \alpha, \frac, \angle in math segments
    return re.sub(r"\\\\([a-zA-Z]+)", r"\\\1", s)


def fix_tex(tex: str) -> str:
    # First handle display math $$...$$
    def repl_disp(m: re.Match) -> str:
        inner = m.group(1)
        return "$$" + _fix_in_math(inner) + "$$"
    tex = _DISPLAY_MATH.sub(repl_disp, tex)

    # Then handle inline math $...$
    def repl_inl(m: re.Match) -> str:
        inner = m.group(1)
        return "$" + _fix_in_math(inner) + "$"
    tex = _INLINE_MATH.sub(repl_inl, tex)
    return tex


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: fix_math_backslashes.py <tex-file>")
        return 2
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"not found: {p}")
        return 1
    src = p.read_text(encoding="utf-8", errors="strict")
    dst = fix_tex(src)
    if dst != src:
        p.write_text(dst, encoding="utf-8")
        print("[ok] normalized \\cmd -> \cmd inside $...$ and $$...$$")
    else:
        print("[info] no changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

