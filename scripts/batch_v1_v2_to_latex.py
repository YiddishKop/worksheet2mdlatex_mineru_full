from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import tempfile
import re


def run(cmd: list[str]) -> int:
    print('$', ' '.join(cmd))
    return subprocess.call(cmd)


def process_one(md_path: Path) -> int:
    stem = md_path.stem
    # Prefer new scheme: <n>_<doc>_<label>.md -> same stem with .latex
    out_latex = md_path.with_suffix('.latex')
    # If old scheme md_part_<doc>_<label>_<n>.md, convert to <n>_<doc>_<label>.latex
    if stem.startswith('md_part_'):
        m = re.search(r'_(\d+)$', stem)
        if m:
            n = m.group(1)
            core = stem[len('md_part_'):]  # <doc>_<label>_<n>
            core_wo_n = core[:-(len(n) + 1)]  # strip _<n>
            new_stem = f"{n}_{core_wo_n}"
            out_latex = md_path.parent / (new_stem + '.latex')
    # Use a temporary file for v1 output so no *.v1.md remains in repo
    with tempfile.TemporaryDirectory() as tdir:
        tmp1 = Path(tdir) / (md_path.stem + '.v1.md')
        # v1: wrap unicode-like math into $...$
        rc = run([sys.executable, '-m', 'scripts.v1_fix_math_dollor', str(md_path), str(tmp1)])
        if rc != 0:
            print(f'[v1] FAIL: {md_path} rc={rc}')
            return rc
        # v2: map unicode inside math to LaTeX commands and convert md images -> \includegraphics
        rc = run([sys.executable, '-m', 'scripts.v2_fix_uni_to_latex', str(tmp1), str(out_latex)])
        if rc != 0:
            print(f'[v2] FAIL: {md_path} rc={rc}')
            return rc
    print(f'[OK] {out_latex}')
    return 0


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    db = repo / 'qs_DB'
    if not db.exists():
        print(f'not found: {db}')
        return 1
    # Only process files in per-document subfolders: qs_DB/<doc_name>/*.md
    mds = sorted(p for p in db.glob('*/*.md') if not p.name.endswith('.v1.md'))
    if not mds:
        print('[batch v1+v2] no md files under qs_DB')
        return 0
    failures = 0
    for md in mds:
        rc = process_one(md)
        if rc != 0:
            failures += 1
    # remove any historical *.v1.md left in qs_DB
    removed = 0
    for p in db.rglob('*.v1.md'):
        try:
            p.unlink()
            removed += 1
        except Exception:
            pass
    print(f'[batch v1+v2] done: {len(mds)} files, failures={failures}, removed_v1_md={removed}')
    return 0 if failures == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
