from __future__ import annotations
import re
from pathlib import Path
import sys

# 目标：
# - 将“题号/标签”与其后的题干合并为一行（去掉中间空行），小问段落保持独立；
# - 若缺失“例题”标题但出现连续小问，则自动补一个“例N 例题 …”标题；
# - 若直接出现小问且前无题干，则在第一道小问前插入“例N 例题 请解答下列各题：”。

# 标题/标签匹配
TITLE_BRACKETED = re.compile(r"^\s*【\s*([^】]+?)\s*】\s*$")
# Regular expressions for matching different title formats
TITLE_LABELED = re.compile(
    r"""^\s*                     # Start of line and optional whitespace
        (                        # Capturing group for the entire label
            (?:例题?\d+(?:-\d+)?)| # Example number with optional range
            (?:练习\d+(?:-\d+)?)| # Exercise number with optional range
            (?:变式\d+(?:-\d+)?)  # Variation number with optional range
        )
        \s*                      # Optional whitespace
        (?:[：:\.．、\)])?        # Optional ending punctuation
        \s*$                     # Optional whitespace and end of line""",
    re.VERBOSE
)

TITLE_NUMBERED = re.compile(
    r"^\s*(\d+)\s*(?:[\.．、\)])\s*$"  # Simple numbered titles like "1." or "1、"
)

# Accept lines like "1 如图，已知…" as a title line, but gate by safe start words
TITLE_NUMBERED_WITH_TEXT = re.compile(
    r"^\s*(\d+)\s+((?:如图|已知|设|第|题|证明|求|解|若|函数|计算|在)\S.*)$"
)

# Match subquestions that start with numbered parentheses like (1) or （1）
SUB_QUESTION = re.compile(
    r"^\s*[（(]\s*(\d+)\s*[)）]"
)

# Extract example numbers from various formats: 例1, 例题1, 【例1】
EXAMPLE_NO = re.compile(
    r"(?:^|[^\w])(?:例题?|【?例)(\d+)(?:】)?"
)

def _strip_prefix_marks(s: str) -> str:
    """Remove leading quote marks and whitespace from a string."""
    text = s.lstrip()
    # Remove all leading '>' quote marks
    while text.startswith('>'):
        text = text[1:].lstrip()
    # Remove leading Markdown heading marks '#'
    while text.startswith('#'):
        text = text[1:].lstrip()
    return text


def _is_title_line(s: str) -> bool:
    t = _strip_prefix_marks(s)
    return bool(
        TITLE_BRACKETED.match(t)
        or TITLE_LABELED.match(t)
        or TITLE_NUMBERED.match(t)
        or TITLE_NUMBERED_WITH_TEXT.match(t)
    )


def _format_title_prefix(s: str) -> str:
    t = _strip_prefix_marks(s)
    b = TITLE_BRACKETED.match(t)
    if b:
        return f"【{b.group(1).strip()}】"
    l = TITLE_LABELED.match(t)
    if l:
        lab = l.group(1).strip()
        # 例题N → 例N（便于 split 的 例\d+ 命中）
        lab = lab.replace('例题', '例')
        return lab
    n2 = TITLE_NUMBERED_WITH_TEXT.match(t)
    if n2:
        # Preserve the inline stem, normalize number to `N.`
        return f"{n2.group(1)}. {n2.group(2).strip()}"
    m = TITLE_NUMBERED.match(t)
    if m:
        return f"{m.group(1)}."
    return t.strip()


def _is_mergeable_stem_line(s: str) -> bool:
    s = s.strip()
    if not s:
        return False
    if s.startswith(("!", "#", "-", "`")):
        return False
    if SUB_QUESTION.match(s):
        return False
    return True


IMG_LINE = re.compile(r"^\s*!\[[^\]]*\]\([^)]+\)")

def _is_image_line(s: str) -> bool:
    return bool(IMG_LINE.match(s.strip()))


def normalize(md_path: Path) -> int:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    i = 0
    changes = 0
    n = len(lines)
    last_example_no = 0

    while i < n:
        cur = lines[i]
        tcur = _strip_prefix_marks(cur)

        # 跟踪文中已出现的最大例题编号
        m_no = EXAMPLE_NO.search(tcur)
        if m_no:
            try:
                last_example_no = max(last_example_no, int(m_no.group(1)))
            except Exception:
                pass

        # 1) 标题行：合并后续题干
        if _is_title_line(cur):
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            if j < n and _is_mergeable_stem_line(lines[j]):
                prefix = _format_title_prefix(cur)
                merged = f"{prefix} {lines[j].lstrip()}".rstrip()
                out.append(merged)
                i = j + 1
                changes += 1
                continue
            # 无可并入题干：只输出规范化标题，清理紧随空行
            out.append(_format_title_prefix(cur))
            i += 1
            while i < n and not lines[i].strip():
                changes += 1
                i += 1
            continue

        # 2) 缺失标题：本行是题干且后面连续小问 ≥2 → 自动补“例N 例题 题干”
        s = tcur.strip()
        is_heading_or_quote = cur.lstrip().startswith('#') or cur.lstrip().startswith('>')
        if s and (not is_heading_or_quote) and (not _is_title_line(tcur)) and (not SUB_QUESTION.match(s)) and _is_mergeable_stem_line(s):
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            k = j
            sub_count = 0
            while k < n:
                lk = lines[k].strip()
                if not lk:
                    k += 1
                    continue
                if _is_image_line(lk):
                    k += 1
                    continue
                if SUB_QUESTION.match(lk):
                    sub_count += 1
                    k += 1
                    # 跳过任意多空行
                    while k < n:
                        lkk = lines[k].strip()
                        if not lkk or _is_image_line(lkk):
                            k += 1
                            continue
                        break
                    continue
                break
            if sub_count >= 2:
                next_no = (last_example_no + 1) if last_example_no >= 1 else 1
                merged = f"例{next_no} {s}".rstrip()
                out.append(merged)
                last_example_no = next_no
                i = i + 1
                # 仅跳过紧随其后的空行，不移除图片行，避免丢图
                while i < n and not lines[i].strip():
                    changes += 1
                    i += 1
                changes += 1
                continue

        # 3) 若当前就是小问，且前面没有有效标题，则在首个小问 (1)/(（1）) 前合成通用标题
        m_sub = SUB_QUESTION.match(tcur)
        if m_sub:
            # 找 out 中最后一个非空行，若不是标题则插入
            last_nonempty = ""
            for prev in reversed(out):
                if prev.strip():
                    last_nonempty = prev
                    break
            already_titled = False
            if last_nonempty:
                if _is_title_line(last_nonempty) or re.match(r"^\s*例\d+\b", last_nonempty):
                    already_titled = True
            sub_no = 0
            try:
                sub_no = int(m_sub.group(1))
            except Exception:
                sub_no = 0
            # 只在遇到小问编号=1 且尚未有标题时，插入一次题头
            if not already_titled and sub_no == 1:
                next_no = (last_example_no + 1) if last_example_no >= 1 else 1
                synth = f"例{next_no} 请解答以下各题："
                hoisted: list[str] = []
                while out:
                    cand = out[-1]
                    if not cand.strip():
                        out.pop()
                        break
                    tc = _strip_prefix_marks(cand)
                    if _is_title_line(tc) or tc.lstrip().startswith(('>', '#')) or _is_image_line(tc):
                        break
                    if SUB_QUESTION.match(tc):
                        break
                    if not _is_mergeable_stem_line(tc):
                        break
                    hoisted.append(out.pop())
                out.append(synth)
                if hoisted:
                    out.extend(reversed(hoisted))
                last_example_no = next_no
                changes += 1

        # 默认输出当前行
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
