from __future__ import annotations
import re
from pathlib import Path
import sys
import argparse

# 目标：
# - 将“标题/标签+题干”规范后合并为一行，去掉中间空行，最小化视觉断裂，保留语义
# - 在缺失“例题”标题但出现连续小问，则自动补一个“例N 请解答以下各题”；
# - 若直接出现小问且前无题干，则在第一道小问前插入“例N 请解答以下各题：”。

# 标题/标签匹配
TITLE_BRACKETED = re.compile(r"^\s*【\s*([^】]+?)\s*】\s*$")
TITLE_LABELED = re.compile(r"^\s*(例题?\s*\d+(?:-\d+)?)\s*[：:\.、\)]?\s*$")
TITLE_NUMBERED = re.compile(r"^\s*(\d+)\s*[\.、\)）]\s*$")
# MinerU 常见的“1 如图 …”行，仅用于回溯合并/降级
TITLE_NUMBERED_WITH_TEXT = re.compile(r"^\s*(\d+)\s*[\.、\)）]?\s+(\S.*)$")
# Recognize headings like “巩固1/巩固1-2” as titles
TITLE_GONGGU = re.compile(r"^\s*(巩固\s*\d+(?:-\d+)?)\s*[：:\.、\)]?\s*$")

SUB_QUESTION = re.compile(r"^\s*[（(]\s*(\d+)\s*[)）]")
EXAMPLE_NO = re.compile(r"(?:^|[^\w])(?:例题?|练习|变式|巩固)(\d+)(?:[题式])?")


def _strip_prefix_marks(s: str) -> str:
    text = s.lstrip()
    while text.startswith('>'):
        text = text[1:].lstrip()
    while text.startswith('#'):
        text = text[1:].lstrip()
    return text


def _is_title_line(s: str) -> bool:
    t = _strip_prefix_marks(s)
    return bool(
        TITLE_BRACKETED.match(t)
        or TITLE_LABELED.match(t)
        or TITLE_GONGGU.match(t)
        or TITLE_NUMBERED.match(t)
    )


def _format_title_prefix(s: str) -> str:
    t = _strip_prefix_marks(s)
    b = TITLE_BRACKETED.match(t)
    if b:
        return f"【{b.group(1).strip()}】"
    l = TITLE_LABELED.match(t)
    if l:
        lab = l.group(1).strip().replace('例题', '例')
        return lab
    g = TITLE_GONGGU.match(t)
    if g:
        return g.group(1).strip()
    m = TITLE_NUMBERED.match(t)
    if m:
        return f"{m.group(1)}."
    n2 = TITLE_NUMBERED_WITH_TEXT.match(t)
    if n2:
        return f"{n2.group(1)}. {n2.group(2).strip()}"
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


def _demote_numbered_intro(s: str) -> str:
    t = _strip_prefix_marks(s)
    m = TITLE_NUMBERED_WITH_TEXT.match(t)
    if not m:
        return s
    return m.group(2).strip()


def normalize(md_path: Path, out_path: Path | None = None) -> int:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    i = 0
    changes = 0
    n = len(lines)
    last_example_no = 0

    while i < n:
        cur = lines[i]
        tcur = _strip_prefix_marks(cur)

        m_no = EXAMPLE_NO.search(tcur)
        if m_no:
            try:
                last_example_no = max(last_example_no, int(m_no.group(1)))
            except Exception:
                pass

        # 1) 标题行处理
        if _is_title_line(cur):
            # 若连续出现两个“例N …”标题，则视作重复标签，丢弃当前标签以避免被错误切成两题
            tcur2 = _strip_prefix_marks(cur)
            if TITLE_LABELED.match(tcur2):
                prev_nonempty = ""
                for prev in reversed(out):
                    if not prev.strip():
                        continue
                    if _is_image_line(prev):
                        continue
                    prev_nonempty = prev
                    break
                if prev_nonempty and re.match(r"^\s*例\d+\b", _strip_prefix_marks(prev_nonempty)):
                    i += 1
                    changes += 1
                    continue
            # 若是“例N …”标题，尝试把前一条“数字型标题 + 紧随图片行”上提为该例题的题干，并降级数字标题
            # 若是“例N …”标题，尝试把前一条“数字型标题 + 紧随图片行”上提为该例题的题干，并降级数字标题
            tcur2 = _strip_prefix_marks(cur)
            hoisted_prev: list[str] = []
            if TITLE_LABELED.match(tcur2):
                while out and _is_image_line(out[-1]):
                    hoisted_prev.append(out.pop())
                if out:
                    prevt = _strip_prefix_marks(out[-1])
                    if TITLE_NUMBERED.match(prevt) or TITLE_NUMBERED_WITH_TEXT.match(prevt):
                        num_line = out.pop()
                        hoisted_prev.append(_demote_numbered_intro(num_line))
                hoisted_prev.reverse()

            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            if j < n and _is_mergeable_stem_line(lines[j]):
                prefix = _format_title_prefix(cur)
                merged = f"{prefix} {lines[j].lstrip()}".rstrip()
                out.append(merged)
                if hoisted_prev:
                    out.extend(hoisted_prev)
                i = j + 1
                changes += 1
                continue
            out.append(_format_title_prefix(cur))
            if hoisted_prev:
                out.extend(hoisted_prev)
            i += 1
            while i < n and not lines[i].strip():
                changes += 1
                i += 1
            continue

        # 2) 题干无标题：若后续出现至少两个小问，自动补“例N …”
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
                merged = f"例{next_no} 请解答以下各题： {s}".rstrip()
                out.append(merged)
                last_example_no = next_no
                i = i + 1
                while i < n and not lines[i].strip():
                    changes += 1
                    i += 1
                changes += 1
                continue

        # 3) 若直接出现小问 (1)/(（1）) 且前无有效标题，则合成“例N …”并上提前文题干
        m_sub = SUB_QUESTION.match(tcur)
        if m_sub:
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
            if not already_titled and sub_no == 1:
                next_no = (last_example_no + 1) if last_example_no >= 1 else 1
                synth = f"例{next_no} 请解答以下各题："
                hoisted: list[str] = []
                while out:
                    cand = out[-1]
                    if not cand.strip():
                        out.pop()
                        continue
                    tc = _strip_prefix_marks(cand)
                    if _is_title_line(tc) or tc.lstrip().startswith(('>', '#')):
                        break
                    if SUB_QUESTION.match(tc):
                        break
                    # Hoist images and mergeable stem lines
                    if _is_image_line(tc) or _is_mergeable_stem_line(tc):
                        hoisted.append(out.pop())
                        continue
                    break
                out.append(synth)
                if hoisted:
                    out.extend(reversed(hoisted))
                last_example_no = next_no
                changes += 1

        out.append(cur)
        i += 1

    if changes or out_path is not None:
        target = out_path or md_path
        target.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changes


def main() -> int:
    ap = argparse.ArgumentParser(description="Normalize titles; optional split into qs_DB")
    ap.add_argument("md", nargs="?", default="outputs/worksheet.md", help="Markdown file to normalize")
    ap.add_argument("--write_to", help="Write normalized output to this path (does not modify source)")
    ap.add_argument("--split_after", action="store_true", help="After normalize, split into qs_DB parts")
    args = ap.parse_args()

    md = Path(args.md)
    if not md.exists():
        print(f"not found: {md}")
        return 1
    out_path = Path(args.write_to) if args.write_to else None
    changes = normalize(md, out_path=out_path)
    print(f"[normalize-md] merged_titles={changes}")

    if args.split_after:
        try:
            from scripts.split_md_to_parts import split_md as _split
        except Exception as e:
            print(f"[normalize-md] split_after failed to import splitter: {e}")
            return 2
        out_root = Path(__file__).resolve().parents[1] / "qs_DB"
        effective_md = out_path or md
        doc_name = effective_md.parent.parent.name if effective_md.parent.parent.name else effective_md.stem
        paths = _split(effective_md, out_root, doc_name)
        print(f"[normalize-md] split parts: {len(paths)} -> {out_root / doc_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


