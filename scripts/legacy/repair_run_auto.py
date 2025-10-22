from pathlib import Path
p = Path('scripts/run_auto.py')
s = p.read_text(encoding='utf-8')
s = s.replace('])`r`n    run([', '])\n    run([')
s = s.replace('ensure_unicode_mappings", str(out_tex)])`r`n', 'ensure_unicode_mappings", str(out_tex)])\n')
p.write_text(s, encoding='utf-8')
print('fixed')
