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
    r"答案[:：]?|解析[:：]?|详解[:：]?|解法\s*(?:\d+|[一二三四五六七八九十]+)\s*[:：]?|参考答案[:：]?"
    r")"
    r")\s*"
)


def _sanitize_filename_part(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", s)
    return s.strip("-")[:80] or "part"


def _adjust_image_links_for_depth(text: str, depth_delta: int = 1) -> str:
    if depth_delta <= 0:
        return text
    prefix = "../" * depth_delta

    def repl(m: re.Match) -> str:
        alt, openb, url, closeb = m.group(1), m.group(2) or "", m.group(3), m.group(4) or ""
        u = (url or "").strip()
        if u.startswith("../qs_image_DB/"):
            u = prefix + u
        elif u.startswith("qs_image_DB/"):
            u = prefix + u
        elif u.startswith("./qs_image_DB/"):
            u = prefix + u[2:]
        return f"![{alt}]({openb}{u}{closeb})"

    img_pat = re.compile(r"!\[([^\]]*)\]\((<)?([^)>]+)(>)?\)")
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
    matches = list(LABEL_PATTERN.finditer(text))
    if not matches:
        return []
    starts = [m.start() for m in matches] + [len(text)]
    spans = [(starts[i], starts[i + 1]) for i in range(len(starts) - 1)]

    out_dir = out_root / doc_name
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for i, (a, b) in enumerate(spans):
        label_raw = matches[i].group(1) if i < len(matches) else f"part{i+1}"
        label = _sanitize_filename_part(label_raw)
        chunk = text[a:b].lstrip("\n")
        chunk = _adjust_image_links_for_depth(chunk, depth_delta=1)
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

