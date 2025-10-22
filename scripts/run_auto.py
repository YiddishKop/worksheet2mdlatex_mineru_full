from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> int:
    print("$", " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(cwd) if cwd else None)
    if check and p.returncode != 0:
        raise SystemExit(p.returncode)
    return p.returncode


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def do_pandoc_export(md: Path, out_dir: Path, emit_snippet: bool = False) -> Path:
    out_tex = out_dir / "worksheet_pandoc.tex"
    out_pdf = out_dir / "worksheet_pandoc.pdf"

    if not shutil.which("pandoc"):
        print("[WARN] pandoc not found; skipping LaTeX/PDF export.")
        return

    script_dir = Path(__file__).resolve().parent
    lua_filter = script_dir / "filters" / "unicode_to_tex.lua"

    # 1) Markdown -> LaTeX
    run([
        "pandoc",
        str(md),
        "-o",
        str(out_tex),
        "-f",
        "gfm",
        "-t",
        "latex",
        "--standalone",
        "--lua-filter", str(lua_filter),
        "-V",
        "documentclass=article",
        "-V",
        "geometry:margin=2cm",
    ])

    # 2) Clean pandoc-bounded wrappers (pure Python to avoid shell encodings)
    # 2) Minimal post-processing only: remove pandocbounded wrapper
    run([sys.executable, "-m", "scripts.clean_pandocbounded", str(out_tex)])
    # 3) Final cleanup: ensuremath/braces/control-chars, remove stray $$ in CJK lines
    run([sys.executable, "-m", "scripts.cleanup_tex_artifacts", str(out_tex)])

    # 4) Try PDF via XeLaTeX if available; else leave TeX as-is
    if shutil.which("xelatex"):
        if out_pdf.exists():
            try:
                out_pdf.unlink()
            except Exception:
                pass
        run(["xelatex", "-interaction=nonstopmode", "worksheet_pandoc.tex"], cwd=out_dir, check=False)
    else:
        print("[INFO] xelatex not found; skipping PDF build. TeX is ready.")

    return out_tex


def make_snippet(tex_path: Path, out_dir: Path) -> Path:
    """Create a snippet TeX without preamble and without \begin/\end{document}."""
    s = tex_path.read_text(encoding="utf-8", errors="ignore")
    # Split at \begin{document}
    begin = s.find("\\begin{document}")
    end = s.rfind("\\end{document}")
    if begin == -1:
        body = s
    else:
        body = s[begin + len("\\begin{document}"):]
    if end != -1:
        body = body[: body.rfind("\\end{document}")]
    # Trim leading/trailing whitespace
    body = body.strip()
    out = out_dir / "worksheet_snippet.tex"
    out.write_text(body, encoding="utf-8")
    print("[OK] Wrote snippet:", out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Cross-platform runner for worksheet2mdlatex pipeline")
    ap.add_argument("--images_dir", default="images")
    ap.add_argument("--out_dir", default="outputs")
    ap.add_argument("--use_mineru", action="store_true")
    ap.add_argument("--format", default="both", choices=["md", "tex", "both"])
    ap.add_argument("--emit_snippet", action="store_true", help="Also write outputs/worksheet_snippet.tex without preamble and document env")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    images_dir = (repo / args.images_dir).resolve()
    out_dir = (repo / args.out_dir).resolve()
    ensure_dir(out_dir)

    # 1) Run pipeline
    print("[INFO] Running pipeline ...")
    pl_cmd = [
        sys.executable,
        "-m",
        "src.pipeline",
        "--images_dir",
        str(images_dir),
        "--out_dir",
        str(out_dir),
        "--format",
        args.format,
    ]
    if args.use_mineru:
        pl_cmd.append("--use_mineru")
    run(pl_cmd, cwd=repo)

    # 2) Sync image DB and fix links
    print("[INFO] Sync qs_image_DB and fix links ...")
    run([sys.executable, "-m", "scripts.sync_qs_image_db_and_fix_links"], cwd=repo)

    # 3) Regenerate pandoc TeX/PDF from corrected Markdown
    md_path = out_dir / "worksheet.md"
    if md_path.exists():
        print("[INFO] Export via Pandoc based on corrected Markdown ...")
        do_pandoc_export(md_path, out_dir, emit_snippet=args.emit_snippet)
    else:
        print("[WARN] outputs/worksheet.md not found; skip pandoc export.")

    print("[DONE] See outputs/ for results.")


if __name__ == "__main__":
    main()






