from __future__ import annotations
import re
import sys
from pathlib import Path


LABEL_PATTERN = re.compile(
    r"(?m)^\s*(?:>\s*)*"
    r"("  # captured label text
    r"(?:"
    r"\d+[．.]|\d+[)]|"                      # 1. / 1) / 1．
    r"【例\d+】|【练习\d+】|【变式\d*-*\d*】|"  # 【例1】/【练习1】/【变式1-1】
    r"例\d+|练习\d+|变式\d+|"
    r"【答案】|【解析】|【详解】|【参考答案】|"
    r"答案[:：]?|解析[:：]?|详解[:：]?|参考答案[:：]?"
    r")"
    r")\s*"
)


def split_md(md_path: Path, out_dir: Path) -> list[Path]:
    text = md_path.read_text(encoding="utf-8")
    starts = [m.start() for m in LABEL_PATTERN.finditer(text)]
    if not starts:
        return []
    starts.append(len(text))
    spans = [(starts[i], starts[i + 1]) for i in range(len(starts) - 1)]

    out_dir.mkdir(parents=True, exist_ok=True)
    base = md_path.stem
    written: list[Path] = []
    for idx, (a, b) in enumerate(spans, start=1):
        chunk = text[a:b].lstrip("\n")
        if not chunk.endswith("\n"):
            chunk += "\n"
        out_path = out_dir / f"md_part_{base}_{idx}.md"
        out_path.write_text(chunk, encoding="utf-8")
        written.append(out_path)
    return written


def main() -> int:
    md = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("outputs/worksheet.md")
    if not md.exists():
        print(f"not found: {md}")
        return 1
    repo = Path(__file__).resolve().parents[1]
    out_dir = repo / "qs_DB"
    files = split_md(md, out_dir)
    print(f"[split-md] wrote {len(files)} parts into {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

