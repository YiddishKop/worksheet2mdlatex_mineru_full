from __future__ import annotations
import re, os
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
tex = repo / 'outputs' / 'worksheet_pandoc.tex'
db = repo / 'qs_image_DB'
if not tex.exists():
    print('[skip] no outputs/worksheet_pandoc.tex')
    raise SystemExit(0)
# build index
idx = {}
for p in db.rglob('*'):
    if p.is_file() and p.suffix.lower() in {'.jpg','.jpeg','.png','.bmp'}:
        idx[p.name] = p

content = tex.read_text(encoding='utf-8', errors='ignore')
pattern = re.compile(r"\\includegraphics(\[[^\]]*\])?\{([^}]+)\}")

def repl(m: re.Match) -> str:
    opts = m.group(1) or ''
    old = m.group(2)
    base = os.path.basename(old)
    if os.path.splitext(base)[1].lower() not in {'.jpg','.jpeg','.png','.bmp'}:
        return m.group(0)
    p = idx.get(base)
    if not p:
        return m.group(0)
    rel = os.path.relpath(str(p), str(tex.parent)).replace('\\','/')
    return f"\\includegraphics{opts}{{{rel}}}"

newc = pattern.sub(repl, content)
if newc != content:
    tex.write_text(newc, encoding='utf-8')
    print('[ok] patched worksheet_pandoc.tex image paths')
else:
    print('[info] no changes applied')
