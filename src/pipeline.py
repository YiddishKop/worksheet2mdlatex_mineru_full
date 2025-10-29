from __future__ import annotations
from pathlib import Path
import re
import subprocess
import shutil
import time, atexit
from typing import List, Dict, Any, Tuple
import argparse

from .split_questions import cut_questions
from .ocr_extract import run_ocr
from .structure_parser import parse_question_v2 as parse_question
from .export_md import export_markdown
from .export_tex import export_latex
from .utils import ensure_dir
from .mineru_integration import mineru_parse_to_questions

__RUN_T0 = time.perf_counter()
def __print_total_elapsed():
    try:
        elapsed = time.perf_counter() - __RUN_T0
        print(f"[INFO] 总耗时: {elapsed:.2f} s")
    except Exception:
        pass
atexit.register(__print_total_elapsed)


def md_to_pandoc_tex(md_path: Path, out_tex: Path) -> Path | None:
    """Markdown -> LaTeX via Pandoc. Returns out_tex or None."""
    try:
        subprocess.check_call([
            "pandoc",
            str(md_path),
            "-o",
            str(out_tex),
            "-f",
            "gfm",
            "-t",
            "latex",
            "--standalone",
            "-V",
            "documentclass=article",
            "-V",
            "geometry:margin=2cm",
        ])
    except FileNotFoundError:
        print("[WARN] 未找到 pandoc，跳过 LaTeX 导出。")
        return None
    except subprocess.CalledProcessError as e:
        print("[WARN] pandoc 转换失败:", e)
        return None

    try:
        tex = out_tex.read_text(encoding="utf-8", errors="ignore")
        tex = re.sub(r"\\pandocbounded\{([\s\S]*?)\}", r"\1", tex)
        out_tex.write_text(tex, encoding="utf-8")
    except Exception:
        pass
    return out_tex


def process_images(images_dir: Path, tmp_dir: Path) -> List[Path]:
    """Split input images into crops via cut_questions."""
    ensure_dir(tmp_dir)
    outs: list[Path] = []
    for p in sorted(images_dir.glob("*.*")):
        if p.suffix.lower() not in [".png",".jpg",".jpeg",".bmp",".tif",".tiff"]:
            continue
        outs.extend(cut_questions(p, tmp_dir))
    return outs


def ocr_and_structure(crops: List[Path], use_pix2tex: bool) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Run OCR on crops and structure into question dicts."""
    qs: list[dict] = []
    ltx: list[str] = []
    for img in crops:
        o = run_ocr(img, use_pix2tex=use_pix2tex)
        q = parse_question(o.get("text") or "")
        qs.append(q)
        ltx.append(o.get("latex"))
    return qs, ltx


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--format", choices=["md","tex","both"], default="both")
    ap.add_argument("--use_pix2tex", action="store_true")
    ap.add_argument("--use_mineru", action="store_true")
    args = ap.parse_args()

    images_dir = Path(args.images_dir)
    out_dir = Path(args.out_dir)
    ensure_dir(out_dir)
    crops_dir = out_dir / "images"
    ensure_dir(crops_dir)

    repo_root = Path(__file__).resolve().parents[1]
    qs_image_db = repo_root / "qs_image_DB"
    ensure_dir(qs_image_db)

    # Minor elapsed print for this run
    t0 = time.perf_counter()
    def _print_elapsed():
        elapsed = time.perf_counter() - t0
        print(f"[INFO] 总耗时: {elapsed:.2f} s")
    atexit.register(_print_elapsed)

    if args.use_mineru:
        qs: list[dict] = []
        ltx: list[str] = []
        imgs: list[Path | None] = []
        for page in sorted(images_dir.glob("*.*")):
            blocks = mineru_parse_to_questions(page, out_dir / "_mineru_tmp")
            auto_dir = out_dir / "_mineru_tmp" / page.stem / "auto"
            # image handling and URL rewrite
            for idx, b in enumerate(blocks):
                text = b.get("text") or ""
                img_paths: list[Path] = []
                for m in re.finditer(r"!\[[^\]]*\]\((?:<([^>]+)>|([^)]+))\)", text):
                    relp = (m.group(1) or m.group(2) or "").strip()
                    if relp.startswith("./"):
                        relp = relp[2:]
                    p = (auto_dir / relp).resolve()
                    if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp"] and p.exists():
                        img_paths.append(p)
                if img_paths:
                    img_paths.sort(key=lambda p: p.stat().st_size, reverse=True)
                    chosen = img_paths[0]
                    dst_name = f"{page.stem}_{idx}_{chosen.name}"
                    dst_path = crops_dir / dst_name
                    try:
                        if not dst_path.exists():
                            shutil.copy2(chosen, dst_path)
                    except Exception:
                        pass
                    # also copy into qs_image_DB with doc structure
                    try:
                        rel_from_mineru = chosen.resolve().relative_to((out_dir / "_mineru_tmp").resolve())
                        dst_in_db = qs_image_db / rel_from_mineru
                        ensure_dir(dst_in_db.parent)
                        if not dst_in_db.exists():
                            shutil.copy2(chosen, dst_in_db)
                    except Exception:
                        pass
                try:
                    def _repl(md):
                        alt = md.group(1)
                        relp = ((md.group(2) or md.group(3) or "")).strip()
                        if relp.startswith("./"):
                            relp = relp[2:]
                        new_url = relp
                        try:
                            mineru_root = (out_dir / "_mineru_tmp").resolve()
                            p = (auto_dir / relp).resolve()
                            rel_from_mineru = p.relative_to(mineru_root)
                            target = (qs_image_db / rel_from_mineru).resolve()
                            new_url = ("../" + target.relative_to(repo_root.resolve()).as_posix())
                        except Exception:
                            pass
                        needs_brackets = any(ord(ch) > 127 for ch in new_url) or (" " in new_url)
                        return f"![{alt}](<{new_url}>)" if needs_brackets else f"![{alt}]({new_url})"
                    text = re.sub(r"!\[([^\]]*)\]\((?:<([^>]+)>|([^)]+))\)", _repl, text)
                except Exception:
                    pass
                q = parse_question(text)
                qs.append(q)
                ltx.append(None)
                imgs.append(None)

        if args.format in ("md", "both"):
            md = export_markdown(qs, imgs, ltx, out_dir)
            print("[OK] 导出 Markdown:", md)
            pandoc_tex = md_to_pandoc_tex(md, out_dir / "worksheet_pandoc.tex")
            if pandoc_tex:
                print("[OK] Pandoc LaTeX:", pandoc_tex)
        if args.format in ("tex", "both"):
            tex = export_latex(qs, imgs, ltx, out_dir)
            print("[OK] 导出 LaTeX:", tex)
        return

    # Non-MinerU branch: cut, OCR, export
    crops = process_images(images_dir, crops_dir)
    if not crops:
        print("未在 images_dir 找到可处理的图片")
        return
    qs, ltx = ocr_and_structure(crops, args.use_pix2tex)
    if args.format in ("md", "both"):
        md = export_markdown(qs, crops, ltx, out_dir)
        print("[OK] 导出 Markdown:", md)
        pandoc_tex = md_to_pandoc_tex(md, out_dir / "worksheet_pandoc.tex")
        if pandoc_tex:
            print("[OK] Pandoc LaTeX:", pandoc_tex)
    if args.format in ("tex", "both"):
        tex = export_latex(qs, crops, ltx, out_dir)
        print("[OK] 导出 LaTeX:", tex)

if __name__ == "__main__":
    main()

