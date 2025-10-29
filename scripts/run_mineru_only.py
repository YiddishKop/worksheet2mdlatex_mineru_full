from __future__ import annotations
from pathlib import Path
import argparse

from src.mineru_integration import run_mineru_on_file
from src.utils import ensure_dir


def _iter_inputs(root: Path, recursive: bool, only_pdf: bool):
    patterns = ["*.pdf"] if only_pdf else ["*.*"]
    if recursive:
        for pat in patterns:
            for p in root.rglob(pat):
                yield p
    else:
        for pat in patterns:
            for p in root.glob(pat):
                yield p


def main() -> int:
    ap = argparse.ArgumentParser(description="Run MinerU only to produce outputs/_mineru_tmp (no worksheet.md)")
    ap.add_argument("--images_dir", required=True, help="Directory containing PDFs/images. Can be a root folder.")
    ap.add_argument("--out_dir", required=True, help="Working output directory (will write to out/_mineru_tmp)")
    ap.add_argument("--recursive", action="store_true", help="Recurse into subdirectories under images_dir")
    ap.add_argument("--only_pdf", action="store_true", help="Only process *.pdf files")
    args = ap.parse_args()

    images = Path(args.images_dir)
    out_dir = Path(args.out_dir)
    mineru_root = out_dir / "_mineru_tmp"
    ensure_dir(mineru_root)

    ok = 0
    inputs = []
    if images.is_file():
        inputs = [images]
    else:
        inputs = list(_iter_inputs(images, args.recursive, args.only_pdf))
    for f in sorted(inputs):
        if not f.is_file():
            continue
        work_dir = mineru_root / f.stem
        ensure_dir(work_dir)
        res = run_mineru_on_file(f, work_dir)
        if res is not None:
            ok += 1
            print(f"[OK] MinerU parsed: {f}")
        else:
            print(f"[WARN] MinerU failed: {f}")
    print(f"[DONE] MinerU-only finished. Parsed {ok} files. See {mineru_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
