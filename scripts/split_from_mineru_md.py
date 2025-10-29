from __future__ import annotations
from pathlib import Path
import argparse
from typing import List

# Import existing helpers
from scripts.normalize_md_question_titles import normalize as norm_titles
from scripts.split_md_to_parts import split_md as split_parts
from scripts.sync_qs_image_db_and_fix_links import (
    sync_mineru_tmp_to_db,
    cleanup_non_image_in_db,
)


def find_mineru_auto_mds(base: Path) -> List[Path]:
    """Find MinerU auto/*.md under outputs/_mineru_tmp/<doc>/<doc>/auto/*.md"""
    if not base.exists():
        return []
    mds: List[Path] = []
    for p in base.rglob("auto/*.md"):
        try:
            rel = p.relative_to(base)
        except Exception:
            continue
        parts = rel.parts
        if len(parts) >= 3:
            mds.append(p)
    return sorted(mds)


def doc_name_from_md(md_path: Path) -> str:
    try:
        return md_path.parent.parent.name
    except Exception:
        return md_path.stem


def run_one(md_path: Path, repo_root: Path) -> None:
    # Write normalized content to a temporary file; keep MinerU MD immutable
    tmp_norm = repo_root / "outputs" / "_tmp_split" / (md_path.stem + ".normalized.md")
    tmp_norm.parent.mkdir(parents=True, exist_ok=True)
    norm_titles(md_path, out_path=tmp_norm)
    sync_mineru_tmp_to_db(repo_root)
    cleanup_non_image_in_db(repo_root)
    out_root = repo_root / "qs_DB"
    doc_name = doc_name_from_md(md_path)
    split_parts(tmp_norm, out_root, doc_name)
    try:
        tmp_norm.unlink(missing_ok=True)
        # Try remove dir if empty
        if not any(tmp_norm.parent.iterdir()):
            tmp_norm.parent.rmdir()
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Normalize and split directly from MinerU auto/*.md")
    ap.add_argument("--md_path", help="Path to MinerU auto/*.md; when omitted, auto-detect under outputs/_mineru_tmp")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    if args.md_path:
        md = Path(args.md_path)
        if not md.exists():
            print(f"[ERROR] md not found: {md}")
            return 2
        run_one(md, repo_root)
        print(f"[OK] Split from: {md}")
        return 0

    base = repo_root / "outputs" / "_mineru_tmp"
    mds = find_mineru_auto_mds(base)
    if not mds:
        print(f"[ERROR] No MinerU auto/*.md found under {base}")
        return 3
    for md in mds:
        run_one(md, repo_root)
        print(f"[OK] Split from: {md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
