from __future__ import annotations
import re
import sys
from pathlib import Path


# 顶层锚点（标题/标签类）：例/练习/变式/答案/解析/详解/参考答案
LABEL_PATTERN = re.compile(
    r"(?m)^\s*(?:>\s*)*(?:#+\s*)?"  # 引用/标题前缀
    r"(?:"
    r"【例\d+】|【练习\d+】|【变式\d+(?:-\d+)?】|"        # 【例1】/【练习1】/【变式1-2】
    r"(?:例|练习|变式)\d+|"                             # 例1/练习1/变式1
    r"【答案】|【解析】|【详解】|【参考答案】|"               # 明确标签
    r"(?:答案|解析|详解|参考答案)[:：]?|"                   # 非括号形式
    r"[0-9\uFF10-\uFF19]+\s*[\.．]\s*"                 # 数字 + 半角./全角． (+可选空格)
    r"(?:如图|如图所示|已知|设|证明|证|求|解|若|函数|计算|求值|化简|作图|画|判断|选择|填空|列方程|解方程|解不等式|求最值|求最大值|求最小值|探究|分析|写出|求出|在|关于|如下|如右图|如上图)"
    r")\s*"
)

# 数字类锚点（回退策略）：如 1. / 1． / 1) / １． （后接至少一个非空白）
NUM_ANCHOR_PATTERN = re.compile(
    r"(?m)^\s*(?:>\s*)*(?:#+\s*)?"      # 引用/标题前缀
    r"[0-9\uFF10-\uFF19]+\s*[\.．、\)）]\s*\S"
)


def _sanitize_filename_part(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", s)
    return s.strip("-")[:80] or "part"


def _rewrite_images_to_db(text: str, doc_name: str, depth_from_qs_db: int = 1) -> str:
    """Rewrite any image URL to flattened DB path:
    ../../qs_image_DB/<doc_name>/<basename>

    Robust to URLs wrapped in angle brackets and containing parentheses, e.g.:
    ![](<../qs_image_DB/文档/auto/images/a.jpg>)
    """
    prefix = "../" * (depth_from_qs_db + 1)
    img_pat = re.compile(r"!\[([^\]]*)\]\((?:<([^>]+)>|([^)]+))\)")

    def repl(m: re.Match) -> str:
        alt = m.group(1)
        url = (m.group(2) or m.group(3) or "").strip()
        basename = url.split('/')[-1].strip()
        new_url = f"{prefix}qs_image_DB/{doc_name}/{basename}"
        needs_brackets = any(ord(ch) > 127 for ch in new_url) or (" " in new_url)
        if needs_brackets:
            return f"![{alt}](<{new_url}>)"
        return f"![{alt}]({new_url})"

    return img_pat.sub(repl, text)


def _detect_doc_name(repo_root: Path) -> str:
    images_dir = repo_root / "images"
    cand = [p for p in images_dir.glob("*.*") if p.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}]
    if len(cand) == 1:
        return cand[0].stem
    pdfs = [p for p in cand if p.suffix.lower() == ".pdf"]
    if pdfs:
        return pdfs[0].stem
    return cand[0].stem if cand else "worksheet"


def split_md(md_path: Path, out_root: Path, doc_name: str) -> list[Path]:
    text = md_path.read_text(encoding="utf-8")

    # 规范化全角数字与标点到半角（等长替换，索引稳定）
    trans = str.maketrans({
        "\uFF10": "0", "\uFF11": "1", "\uFF12": "2", "\uFF13": "3", "\uFF14": "4",
        "\uFF15": "5", "\uFF16": "6", "\uFF17": "7", "\uFF18": "8", "\uFF19": "9",
        "\uFF0E": ".",  # ．
        "\u3002": ".",  # 。
        "\uFF09": ")",  # ）
        "\uFF08": "(",  # （
    })
    norm = text.translate(trans)

    # 收集锚点位置
    anchors: list[tuple[int, str]] = []
    anchors.extend((m.start(), m.group(0)) for m in LABEL_PATTERN.finditer(norm))
    anchors.extend((m.start(), m.group(0)) for m in NUM_ANCHOR_PATTERN.finditer(norm))
    # 兼容“巩固n/巩固n-m”作为标题
    gg = re.compile(r"(?m)^\s*(?:>\s*)*(?:#+\s*)?(巩固\s*\d+(?:-\d+)?)\s*[\.、\)]?\s*$")
    anchors.extend((m.start(), m.group(1)) for m in gg.finditer(norm))

    if not anchors:
        return []

    # 去重与排序
    pos_to_label: dict[int, str] = {}
    for pos, lab in anchors:
        if pos not in pos_to_label:
            pos_to_label[pos] = lab
    starts_sorted = sorted(pos_to_label.keys()) + [len(text)]
    spans = [(starts_sorted[i], starts_sorted[i + 1]) for i in range(len(starts_sorted) - 1)]

    out_dir = out_root / doc_name
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for i, (a, b) in enumerate(spans):
        label_raw = pos_to_label.get(a, f"part{i+1}")
        label = _sanitize_filename_part(label_raw)
        chunk = text[a:b].lstrip("\n")
        chunk = _rewrite_images_to_db(chunk, doc_name=doc_name, depth_from_qs_db=1)
        if not chunk.endswith("\n"):
            chunk += "\n"
        seq = i + 1
        out_path = out_dir / f"{seq}_{doc_name}_{label}.md"
        out_path.write_text(chunk, encoding="utf-8")
        written.append(out_path)
    return written


def main() -> int:
    md = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("outputs/worksheet.md")
    if not md.exists():
        print(f"not found: {md}")
        return 1
    repo = Path(__file__).resolve().parents[1]
    doc_name = _detect_doc_name(repo)
    out_root = repo / "qs_DB"
    files = split_md(md, out_root, doc_name)
    print(f"[split-md] wrote {len(files)} parts into {out_root / doc_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
