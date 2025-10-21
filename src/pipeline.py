from pathlib import Path
import re
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
        print(f"[INFO] 总用时: {elapsed:.2f} 秒")
    except Exception:
        pass
atexit.register(__print_total_elapsed)

def process_images(images_dir: Path, tmp_dir: Path) -> List[Path]:
    """对 `images_dir` 下的图片进行题块切分并输出到 `tmp_dir`。

    - 仅处理常见图片后缀（png/jpg/jpeg/bmp/tif/tiff），忽略其他文件。
    - 调用 `cut_questions` 对每张图片做粗分割，返回所有切割后的图片路径列表。
    """
    ensure_dir(tmp_dir); outs=[]
    for p in sorted(images_dir.glob("*.*")):
        if p.suffix.lower() not in [".png",".jpg",".jpeg",".bmp",".tif",".tiff"]: continue
        outs.extend(cut_questions(p, tmp_dir))
    return outs

def ocr_and_structure(crops: List[Path], use_pix2tex: bool) -> Tuple[List[Dict[str, Any]], List[str]]:
    """对切分得到的小图执行 OCR，并解析题目结构。

    返回：
    - questions: 结构化题目列表（题号/题干/选项/答案等）。
    - latex: 每张小图识别到的公式 LaTeX 字符串列表（可能含 None）。
    """
    qs=[]; ltx=[]
    for img in crops:
        o=run_ocr(img, use_pix2tex=use_pix2tex)
        q=parse_question(o.get("text") or ""); qs.append(q); ltx.append(o.get("latex"))
    return qs, ltx

def main():
    """命令行入口：组合 MinerU/切图 + OCR + 导出为 Markdown/LaTeX。

    关键参数：
    - --images_dir: 输入目录（图片或 PDF）；
    - --out_dir: 输出目录（会创建）；
    - --format: md/tex/both；
    - --use_pix2tex: 启用本地公式识别；
    - --use_mineru: 使用 MinerU 解析 PDF/整页为题目文本块。
    """
    ap=argparse.ArgumentParser()
    ap.add_argument("--images_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--format", choices=["md","tex","both"], default="both")
    ap.add_argument("--use_pix2tex", action="store_true")
    ap.add_argument("--use_mineru", action="store_true")
    args=ap.parse_args()
    images_dir=Path(args.images_dir); out_dir=Path(args.out_dir); ensure_dir(out_dir)
    crops_dir=out_dir/"images"; ensure_dir(crops_dir)
    # 全局题图资源库（项目根目录）
    repo_root = Path(__file__).resolve().parents[1]
    qs_image_db = repo_root/"qs_image_DB"; ensure_dir(qs_image_db)
    # 运行总用时统计
    import time, atexit
    t0 = time.perf_counter()
    def _print_elapsed():
        elapsed = time.perf_counter() - t0
        print(f"[INFO] 总用时: {elapsed:.2f} 秒")
    atexit.register(_print_elapsed)

    if args.use_mineru:
        qs=[]; ltx=[]; imgs=[]
        pages=[p for p in sorted(images_dir.glob("*.*")) if p.suffix.lower() in [".png",".jpg",".jpeg",".bmp",".tif",".tiff",".pdf"]]
        if not pages: print("未在 images_dir 中找到可处理文件（图片或 PDF）。"); return
        for page in pages:
            blocks=mineru_parse_to_questions(page, out_dir/"_mineru_tmp")
            # 基于分段文本中的 Markdown 图片为每题挑选插图（若无，则不附图）
            auto_dir = out_dir/"_mineru_tmp"/page.stem/"auto"
            # 同步当前页面的 MinerU 产出目录到 qs_image_DB（保留原有层级）
            try:
                mineru_root = out_dir/"_mineru_tmp"
                if auto_dir.exists():
                    rel = auto_dir.resolve().relative_to(mineru_root.resolve())
                    dst_auto = qs_image_db/rel
                    ensure_dir(dst_auto)
                    for src_path in auto_dir.rglob('*'):
                        if src_path.is_file():
                            dst_path = dst_auto/src_path.relative_to(auto_dir)
                            ensure_dir(dst_path.parent)
                            if not dst_path.exists():
                                try:
                                    shutil.copy2(src_path, dst_path)
                                except Exception:
                                    pass
            except Exception:
                pass
            for idx, b in enumerate(blocks):
                text = b.get("text") or ""
                img_paths = []
                for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", text):
                    relp = m.group(1).strip()
                    # 仅处理相对路径 images/*
                    if relp.startswith("./"): relp = relp[2:]
                    p = (auto_dir/relp).resolve()
                    if p.suffix.lower() in [".jpg",".jpeg",".png",".bmp"] and p.exists():
                        img_paths.append(p)
                final_img=None
                if img_paths:
                    # 取体积最大的作为代表图
                    img_paths.sort(key=lambda p: p.stat().st_size, reverse=True)
                    chosen = img_paths[0]
                    dst_name=f"{page.stem}_{idx}_{chosen.name}"
                    dst_path=crops_dir/dst_name
                    try:
                        if not dst_path.exists():
                            shutil.copy2(chosen, dst_path)
                        final_img = dst_path if dst_path.exists() else None
                    except Exception:
                        final_img=None
                # 将代表图复制/指向到全局图片库 qs_image_DB，并使用其路径作为最终引用
                if img_paths:
                    try:
                        img_paths.sort(key=lambda p: p.stat().st_size, reverse=True)
                        chosen2 = img_paths[0]
                        rel_from_mineru = chosen2.resolve().relative_to((out_dir/"_mineru_tmp").resolve())
                        dst_in_db = qs_image_db/rel_from_mineru
                        ensure_dir(dst_in_db.parent)
                        if not dst_in_db.exists():
                            shutil.copy2(chosen2, dst_in_db)
                        if dst_in_db.exists():
                            final_img = dst_in_db
                    except Exception:
                        pass
                # 将题干内的 Markdown 图片链接改写为指向仓库根的 qs_image_DB，确保渲染全部图片
                try:
                    def _repl(md: re.Match) -> str:
                        alt = md.group(1)
                        relp = (md.group(2) or "").strip()
                        if relp.startswith("./"):
                            relp = relp[2:]
                        new_url = relp
                        try:
                            mineru_root = (out_dir/"_mineru_tmp").resolve()
                            p = (auto_dir/relp).resolve()
                            rel_from_mineru = p.relative_to(mineru_root)
                            target = (qs_image_db/rel_from_mineru).resolve()
                            new_url = ("../" + target.relative_to(repo_root.resolve()).as_posix())
                        except Exception:
                            pass
                        return f"![{alt}]({new_url})"
                    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _repl, text)
                except Exception:
                    pass
                q=parse_question(text); qs.append(q); ltx.append(None); imgs.append(None)
        if args.format in ("md","both"):
            md=export_markdown(qs, imgs, ltx, out_dir); print("[OK] 导出 Markdown:", md)
        if args.format in ("tex","both"):
            tex=export_latex(qs, imgs, ltx, out_dir); print("[OK] 导出 LaTeX:", tex)
        return

    crops=process_images(images_dir, crops_dir)
    if not crops: print("未在 images_dir 中找到可处理图片。"); return
    qs,ltx=ocr_and_structure(crops, args.use_pix2tex)
    if args.format in ("md","both"):
        md=export_markdown(qs, crops, ltx, out_dir); print("[OK] 导出 Markdown:", md)
    if args.format in ("tex","both"):
        tex=export_latex(qs, crops, ltx, out_dir); print("[OK] 导出 LaTeX:", tex)

if __name__=="__main__": main()
