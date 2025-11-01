from __future__ import annotations
import subprocess
from pathlib import Path
import sys


def convert_one(md_path: Path) -> int:
    tex_path = md_path.with_suffix('.tex')
    cmd = [
        'pandoc',
        str(md_path),
        '-f', 'markdown',
        '-t', 'latex',
        '--ascii',
        '--pdf-engine=pdflatex',  # harmless when output is .tex (kept to match requested cmd)
        '-o', str(tex_path),
    ]
    print('$', ' '.join(cmd))
    return subprocess.call(cmd)


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
