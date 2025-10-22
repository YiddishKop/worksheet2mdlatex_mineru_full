from __future__ import annotations
from pathlib import Path
import sys


INJECT_MARK = "% -- Injected unicode mappings --"


def ensure_mappings(tex_path: Path) -> bool:
    s = tex_path.read_text(encoding="utf-8", errors="strict")
    if INJECT_MARK in s:
        return False

    lines = s.splitlines()
    out = []
    injected = False
    for line in lines:
        out.append(line)
        # After unicode-math load (XeTeX/LuaTeX branch) or after \usepackage{iftex}
        if not injected and "\\usepackage{unicode-math}" in line:
            out.append(INJECT_MARK)
            out.append("\\usepackage{newunicodechar}")
            # Map △ (U+25B3) and ∠ (U+2220)
            out.append("\\newunicodechar{△}{\\ensuremath{\\triangle}}")
            out.append("\\newunicodechar{∠}{\\ensuremath{\\angle}}")
            injected = True
    if injected:
        tex_path.write_text("\n".join(out), encoding="utf-8")
    return injected


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: ensure_unicode_mappings.py <tex-file>")
        return 2
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"not found: {p}")
        return 1
    changed = ensure_mappings(p)
    print("unicode-mappings:" + ("injected" if changed else "ok"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
