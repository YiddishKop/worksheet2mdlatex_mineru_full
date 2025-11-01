from __future__ import annotations
import re
from pathlib import Path
import sys


def insert_breaks(text: str) -> tuple[str, int]:
    # Insert a newline before inline "解析：" when not already at line start
    # and before inline "解法<n>：" (n is digits). Handle both full-width and ASCII colons.
    count = 0

    def _repl_parse(m: re.Match) -> str:
        nonlocal count
        count += 1
        return m.group(1) + "\n" + m.group(2)

    def _repl_method(m: re.Match) -> str:
        nonlocal count
        count += 1
        return m.group(1) + "\n" + m.group(2)

    # 解析： 之前加换行（若非行首）
    # ([^\r\n]) 捕获前一个非换行字符；\s* 吃掉其后的空白；(解析[:：]) 捕获目标标签
    text, n1 = re.subn(r"([^\r\n])\s*(解析\s*[：:])", _repl_parse, text)
    # 解法<数字>： 之前加换行（若非行首）
    text, n2 = re.subn(r"([^\r\n])\s*(解法\s*\d+\s*[：:])", _repl_method, text)
    count += n1 + n2  # already added in callbacks; keep consistent
    return text, (n1 + n2)


def main() -> int:
    md = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("outputs/worksheet.md")
    if not md.exists():
        print(f"not found: {md}")
        return 1
    text = md.read_text(encoding="utf-8")
    new_text, added = insert_breaks(text)
    if added:
        md.write_text(new_text, encoding="utf-8")
    print(f"[insert-breaks] inserted={added} file={md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

