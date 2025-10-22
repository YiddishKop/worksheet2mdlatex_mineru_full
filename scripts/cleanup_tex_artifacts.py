from __future__ import annotations
import re
from pathlib import Path
import sys


CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def _unescape_braces(s: str) -> str:
    return s.replace(r"\{", "{").replace(r"\}", "}")


def clean(tex: str) -> str:
    s = tex
    # 1) Strip stray control characters (from bad OCR or conversion)
    s = CONTROL_CHARS.sub("", s)
    # 2) Turn literal \textbackslash{}X back into \X
    s = s.replace(r"\textbackslash{}", "\\")
    # 3a) Replace ensuremath with escaped braces: \ensuremath\{ ... \} -> $...$
    def _repl_esc(m: re.Match) -> str:
        inner = _unescape_braces(m.group(1))
        return f"${inner}$"
    s = re.sub(r"\\ensuremath\s*\\\{([\s\S]*?)\\\}", _repl_esc, s)
    # 3b) Replace normal ensuremath: \ensuremath{ ... } -> $...$
    s = re.sub(r"\\ensuremath\s*\{([\s\S]*?)\}", lambda m: f"${m.group(1)}$", s)
    # 4) After conversions, unescape any remaining \{ \} to { }
    s = _unescape_braces(s)
    # 5) Collapse duplicated $$ from previous conversions (optional safety)
    s = s.replace("$$$$", "$$")
    # 6) Remove stray inline '$$' created by empty math after control-char removal.
    #    Heuristic: if a line contains CJK and a single '$$' and the line isn't just '$$', drop that '$$'.
    lines = s.splitlines(True)
    out_lines: list[str] = []
    cjk = re.compile(r"[\u3400-\u9FFF]")
    for ln in lines:
        if ln.count("$$") == 1 and ln.strip() != "$$" and cjk.search(ln):
            ln = ln.replace("$$", "")
        out_lines.append(ln)
    s = "".join(out_lines)
    return s


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: cleanup_tex_artifacts.py <tex-file>")
        return 2
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"not found: {p}")
        return 1
    src = p.read_text(encoding="utf-8", errors="strict")
    dst = clean(src)
    if dst != src:
        p.write_text(dst, encoding="utf-8")
        print("[ok] cleaned artifacts (controls, ensuremath, escaped braces)")
    else:
        print("[info] no changes needed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

