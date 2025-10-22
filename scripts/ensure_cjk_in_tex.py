import sys
from pathlib import Path

def ensure_cjk(tex_path: Path) -> None:
    s = tex_path.read_text(encoding='utf-8', errors='ignore')
    # Remove lmodern when using unicode-math/fontspec to avoid conflicts
    s = s.replace('\\usepackage{lmodern}', '')
    lines = s.splitlines()
    out = []
    injected = ('xeCJK' in s)
    for i, line in enumerate(lines):
        out.append(line)
        if not injected and '\\usepackage{unicode-math}' in line:
            # Robust font setup with fallbacks
            out.append('% -- Injected XeCJK + font fallbacks --')
            out.append('\\usepackage[BoldFont,SlantFont]{xeCJK}')
            out.append('\\IfFontExistsTF{SimSun}{\\setCJKmainfont{SimSun}}{\\IfFontExistsTF{Noto Serif CJK SC}{\\setCJKmainfont{Noto Serif CJK SC}}{\\IfFontExistsTF{Microsoft YaHei}{\\setCJKmainfont{Microsoft YaHei}}{}}}')
            out.append('\\IfFontExistsTF{SimSun}{\\setmainfont{SimSun}}{\\IfFontExistsTF{Noto Serif CJK SC}{\\setmainfont{Noto Serif CJK SC}}{\\IfFontExistsTF{Microsoft YaHei}{\\setmainfont{Microsoft YaHei}}{}}}')
            out.append('\\IfFontExistsTF{XITS Math}{\\setmathfont{XITS Math}}{\\IfFontExistsTF{STIX Two Math}{\\setmathfont{STIX Two Math}}{\\IfFontExistsTF{Latin Modern Math}{\\setmathfont{Latin Modern Math}}{\\IfFontExistsTF{TeX Gyre Termes Math}{\\setmathfont{TeX Gyre Termes Math}}{\\IfFontExistsTF{Libertinus Math}{\\setmathfont{Libertinus Math}}{}}}}}')
            injected = True
    if injected:
        tex_path.write_text('\n'.join(out), encoding='utf-8')

if __name__ == '__main__':
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('outputs/worksheet_pandoc.tex')
    if p.exists():
        ensure_cjk(p)
