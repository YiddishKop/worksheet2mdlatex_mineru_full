from __future__ import annotations
import re
from pathlib import Path
import sys

# 这里是把题号和题干合并到一行的脚本，为了后续切题方便
TITLE_BRACKETED = re.compile(r"^\s*【([^】]+)】\s*$")
TITLE_NUMBERED = re.compile(r"^\s*(\d+)\s*[\.．、]\s*$")


def should_merge_with_next(line: str) -> bool:
    if TITLE_BRACKETED.match(line):
        return True
    if TITLE_NUMBERED.match(line):
        return True
    return False


def is_mergeable_text(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    # Avoid merging into images or headings/lists/code fences
    if s.startswith("!") or s.startswith("#") or s.startswith("-") or s.startswith("`"):
        return False
    return True


def normalize(md_path: Path) -> int:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    i = 0
    changes = 0
    n = len(lines)
    while i < n:
        cur = lines[i]
        if should_merge_with_next(cur) and i + 1 < n:
            # Find next non-empty line index j (allow at most one blank)
            j = i + 1
            if j < n and not lines[j].strip() and (j + 1) < n:
                j += 1
            if j < n and is_mergeable_text(lines[j]):
                b = TITLE_BRACKETED.match(cur)
                m = TITLE_NUMBERED.match(cur)
                if b:
                    prefix = f"【{b.group(1).strip()}】"
                elif m:
                    prefix = f"{m.group(1)}."
                else:
                    prefix = cur.strip()
                merged = f"{prefix} {lines[j].lstrip()}".rstrip()
                out.append(merged)
                i = j + 1
                changes += 1
                continue
        out.append(cur)
        i += 1

    if changes:
        md_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changes


def main() -> int:
    md = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("outputs/worksheet.md")
    if not md.exists():
        print(f"not found: {md}")
        return 1
    changes = normalize(md)
    print(f"[normalize-md] merged_titles={changes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

