from __future__ import annotations
import re
from pathlib import Path
import sys


def comment_preamble(tex_path: Path) -> bool:
    s = tex_path.read_text(encoding="utf-8", errors="strict")
    # Find \begin{document}
    m = re.search(r"^\\begin\{document\}\s*$", s, flags=re.MULTILINE)
    if not m:
        return False
    head = s[:m.start()]
    tail = s[m.start():]
    # Comment every non-empty line in head (preserve empty lines)
    commented_lines = []
    for line in head.splitlines(True):  # keepends
        if line.strip() and not line.lstrip().startswith('%'):
            commented_lines.append('% ' + line)
        else:
            commented_lines.append(line)
    out = ''.join(commented_lines) + tail
    if out != s:
        tex_path.write_text(out, encoding="utf-8")
        return True
    return False


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: comment_preamble.py <tex-file>")
        return 2
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"not found: {p}")
        return 1
    changed = comment_preamble(p)
    print("[ok] preamble commented" if changed else "[info] no change")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

