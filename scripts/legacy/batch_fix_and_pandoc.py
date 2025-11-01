from __future__ import annotations
import subprocess
from pathlib import Path
import sys


def run(cmd: list[str]) -> int:
    print('$', ' '.join(cmd))
    return subprocess.call(cmd)


def process_md(md_path: Path) -> Path:
    tmp1 = md_path.with_suffix('.v1.md')
    tmp2 = md_path.with_suffix('.v2.md')
    # v1: wrap unicode-like math into $...$
    rc = run([sys.executable, '-m', 'scripts.v1_fix_math_dollor', str(md_path), str(tmp1)])
    if rc != 0:
        raise SystemExit(f'v1_fix failed for {md_path} rc={rc}')
    # v2: map unicode inside math to LaTeX commands and normalize
    rc = run([sys.executable, '-m', 'scripts.v2_fix_uni_to_latex', str(tmp1), str(tmp2)])
    if rc != 0:
        raise SystemExit(f'v2_fix failed for {md_path} rc={rc}')
    return tmp2


def convert_one(md_path: Path) -> int:
    fixed_md = process_md(md_path)
    out_tex = md_path.with_suffix('.tex')
    cmd = [
        'pandoc',
        str(fixed_md),
        '-f', 'markdown',
        '-t', 'latex',
        '--ascii',
        '--pdf-engine=pdflatex',
        '-o', str(out_tex),
    ]
    return run(cmd)


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    db = repo / 'qs_DB'
    if not db.exists():
        print(f'not found: {db}')
        return 1
    mds = sorted(db.glob('*.md'))
    if not mds:
        print('[batch] no md files under qs_DB')
        return 0
    failures = 0
    for md in mds:
        rc = convert_one(md)
        if rc != 0:
            print(f'[batch] FAIL: {md} (rc={rc})')
            failures += 1
        else:
            print(f'[batch] OK: {md.with_suffix(".tex")}')
    print(f'[batch] done: {len(mds)} files, failures={failures}')
    return 0 if failures == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
