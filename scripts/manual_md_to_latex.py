from __future__ import annotations
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile
import re


def run(cmd: list[str]) -> int:
    print('$', ' '.join(cmd))
    return subprocess.call(cmd)


def derive_out_latex(md_path: Path) -> Path:
    """
    Derive the output .latex path from an input part .md path.
    - New scheme: <n>_<doc>_<label>.md -> same stem with .latex
    - Old scheme: md_part_<doc>_<label>_<n>.md -> <n>_<doc>_<label>.latex
    """
    stem = md_path.stem
    out_latex = md_path.with_suffix('.latex')
    if stem.startswith('md_part_'):
        m = re.search(r'_(\d+)$', stem)
        if m:
            n = m.group(1)
            core = stem[len('md_part_'):]
            core_wo_n = core[:-(len(n) + 1)]
            new_stem = f"{n}_{core_wo_n}"
            out_latex = md_path.parent / (new_stem + '.latex')
    return out_latex


def process_one(md_path: Path, mode: str = 'v1v2') -> int:
    """
    Convert a single qs_DB part .md to .latex.
    mode:
      - 'v1v2' (default): run v1 then v2
      - 'v2': run v2 only (assumes math already delimited)
    """
    out_latex = derive_out_latex(md_path)
    if mode not in ('v1v2', 'v2'):
        print(f"[ERR] Unknown mode: {mode}")
        return 2

    if mode == 'v2':
        return run([sys.executable, '-m', 'scripts.v2_fix_uni_to_latex', str(md_path), str(out_latex)])

    with tempfile.TemporaryDirectory() as tdir:
        tmp1 = Path(tdir) / (md_path.stem + '.v1.md')
        rc = run([sys.executable, '-m', 'scripts.v1_fix_math_dollor', str(md_path), str(tmp1)])
        if rc != 0:
            print(f'[v1] FAIL: {md_path} rc={rc}')
            return rc
        rc = run([sys.executable, '-m', 'scripts.v2_fix_uni_to_latex', str(tmp1), str(out_latex)])
        if rc != 0:
            print(f'[v2] FAIL: {md_path} rc={rc}')
            return rc
    print(f'[OK] {out_latex}')
    return 0


def collect_targets(file: Path | None, dir: Path | None, repo_root: Path) -> list[Path]:
    qs_db = repo_root / 'qs_DB'
    if file:
        return [file]
    if dir:
        return sorted(p for p in dir.glob('*.md') if not p.name.endswith('.v1.md'))
    return sorted(p for p in qs_db.glob('*/*.md') if not p.name.endswith('.v1.md'))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            'Convert qs_DB Markdown parts (.md) to LaTeX (.latex).\n'
            'Default processes all qs_DB/<doc>/*.md with v1+v2.'
        )
    )
    ap.add_argument('--file', dest='file', help='Path to a single part .md to convert')
    ap.add_argument('--dir', dest='dir', help='Path to a qs_DB/<doc> directory to process')
    ap.add_argument('--mode', choices=['v1v2', 'v2'], default='v1v2', help='Conversion mode (default: v1v2)')
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]

    file_path: Path | None = None
    dir_path: Path | None = None
    if args.file:
        file_path = Path(args.file).resolve()
        if not file_path.exists() or file_path.suffix.lower() != '.md':
            print(f"[ERR] --file not found or not .md: {file_path}")
            return 1
    if args.dir:
        dir_path = Path(args.dir).resolve()
        if not dir_path.exists() or not dir_path.is_dir():
            print(f"[ERR] --dir not found or not a directory: {dir_path}")
            return 1

    targets = collect_targets(file_path, dir_path, repo_root)
    if not targets:
        print('[INFO] No Markdown parts found to convert.')
        return 0

    failures = 0
    for md in targets:
        rc = process_one(md, mode=args.mode)
        if rc != 0:
            failures += 1

    removed = 0
    for p in (repo_root / 'qs_DB').rglob('*.v1.md'):
        try:
            p.unlink()
            removed += 1
        except Exception:
            pass
    print(f"[manual-md->latex] done: {len(targets)} files, failures={failures}, removed_v1_md={removed}")
    return 0 if failures == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())

