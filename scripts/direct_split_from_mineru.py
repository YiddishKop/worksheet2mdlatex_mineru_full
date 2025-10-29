from __future__ import annotations
from pathlib import Path
import argparse
import subprocess
import sys
from typing import List, Dict, Any

# Reuse existing repo modules
from src.mineru_integration import mineru_parse_to_questions
from src.structure_parser import parse_question_v2 as parse_question
from src.export_md import export_markdown_to_path
from src.utils import ensure_dir


def build_temp_md_from_mineru(images_dir: Path, out_dir: Path) -> Path:
    """Run MinerU on each file under images_dir, aggregate blocks into a temp Markdown.

    This preserves downstream rules by feeding the same normalization and split scripts.
    Returns the path to the temporary Markdown file.
    """
    ensure_dir(out_dir)
    tmp_md_dir = out_dir / "_tmp_split"
    ensure_dir(tmp_md_dir)
    tmp_md = tmp_md_dir / "worksheet.md"

    qs: List[Dict[str, Any]] = []
    ltx: List[str] = []
    imgs: List[Path | None] = []

    mineru_tmp = out_dir / "_mineru_tmp"
    ensure_dir(mineru_tmp)

    # For each page/file, parse with MinerU into structured text blocks
    for page in sorted(images_dir.glob("*.*")):
        blocks = mineru_parse_to_questions(page, mineru_tmp)
        for b in blocks:
            text = b.get("text") or ""
            q = parse_question(text)
            qs.append(q)
            ltx.append(None)
            imgs.append(None)

    export_markdown_to_path(qs, imgs, ltx, out_dir=out_dir, out_path=tmp_md)
    return tmp_md


def main() -> int:
    ap = argparse.ArgumentParser(description="MinerU -> normalize -> split to qs_DB (no worksheet.md persisted)")
    ap.add_argument("--images_dir", required=True, help="Input directory with images/PDFs for MinerU")
    ap.add_argument("--out_dir", required=True, help="Working outputs directory (will use outputs/_mineru_tmp)")
    args = ap.parse_args()

    images_dir = Path(args.images_dir)
    out_dir = Path(args.out_dir)

    tmp_md = build_temp_md_from_mineru(images_dir, out_dir)

    # 1) Normalize titles (auto insert 例N … and hoist stems)
    try:
        subprocess.run([sys.executable, "-m", "scripts.normalize_md_question_titles", str(tmp_md)], check=False)
    except Exception:
        pass

    # 2) Sync MinerU images into qs_image_DB and fix flattened copies
    try:
        subprocess.run([sys.executable, "-m", "scripts.sync_qs_image_db_and_fix_links"], check=False)
    except Exception:
        pass

    # 3) Split into qs_DB/<doc>/n_*.md using existing splitter (pass explicit md path)
    try:
        subprocess.run([sys.executable, "-m", "scripts.split_md_to_parts", str(tmp_md)], check=False)
    except Exception:
        pass

    # 4) Cleanup temporary markdown (keep _mineru_tmp and qs_DB/ as outputs)
    try:
        if tmp_md.exists():
            tmp_md.unlink()
        try:
            (out_dir / "_tmp_split").rmdir()
        except Exception:
            pass
    except Exception:
        pass

    print("[DONE] Direct split finished. See qs_DB/ for parts and qs_image_DB/ for images.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

