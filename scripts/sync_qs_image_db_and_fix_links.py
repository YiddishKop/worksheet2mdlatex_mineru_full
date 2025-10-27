from __future__ import annotations
import os
import re
import shutil
from pathlib import Path


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def sync_mineru_tmp_to_db(repo_root: Path) -> int:
    """Copy only MinerU `auto/images` files into repo_root/qs_image_DB with flattened layout:
    qs_image_DB/<doc_name>/<image_name>.
    Returns number of files copied (best-effort)."""
    src_root = repo_root / "outputs" / "_mineru_tmp"
    dst_root = repo_root / "qs_image_DB"
    ensure_dir(dst_root)
    if not src_root.exists():
        return 0
    exts = {".jpg", ".jpeg", ".png", ".bmp"}
    copied = 0
    # Find all auto/images folders and copy image files only
    for images_dir in src_root.rglob("auto/images"):
        if not images_dir.is_dir():
            continue
        # Determine doc_name as the first path element under _mineru_tmp
        try:
            rel_from_root = images_dir.relative_to(src_root)
            parts = rel_from_root.parts
            if not parts:
                continue
            doc_name = parts[0]
        except Exception:
            continue
        doc_dst = dst_root / doc_name
        ensure_dir(doc_dst)
        for src in images_dir.rglob("*"):
            if src.is_file() and src.suffix.lower() in exts:
                dst = doc_dst / src.name
                if not dst.exists():
                    try:
                        shutil.copy2(src, dst)
                        copied += 1
                    except Exception:
                        pass
    return copied


def cleanup_non_image_in_db(repo_root: Path) -> int:
    """Remove non-image files under qs_image_DB to keep DB image-only, and flatten legacy layout.
    Also migrates legacy qs_image_DB/<doc>/<doc>/auto/images/*.jpg to qs_image_DB/<doc>/*.jpg.
    Returns number of files removed (non-images) + migrated (counted separately)."""
    db_root = repo_root / "qs_image_DB"
    if not db_root.exists():
        return 0
    exts = {".jpg", ".jpeg", ".png", ".bmp"}
    removed = 0
    # Migrate legacy deep images into flat layout, then remove originals
    for p in list(db_root.rglob("auto/images/*")):
        if p.is_file() and p.suffix.lower() in exts:
            try:
                rel = p.relative_to(db_root)
                parts = rel.parts
                if not parts:
                    continue
                doc_name = parts[0]
                dst = db_root / doc_name / p.name
                ensure_dir(dst.parent)
                if not dst.exists():
                    shutil.copy2(p, dst)
                # delete original deep file
                try:
                    p.unlink()
                except Exception:
                    pass
            except Exception:
                pass
    # Remove non-images anywhere under db_root
    for p in db_root.rglob("*"):
        if p.is_file() and p.suffix.lower() not in exts:
            try:
                p.unlink()
                removed += 1
            except Exception:
                pass
    # Prune empty directories
    for d in sorted([x for x in db_root.rglob("*") if x.is_dir()], key=lambda x: len(x.as_posix().split('/')), reverse=True):
        try:
            if not any(d.iterdir()):
                d.rmdir()
        except Exception:
            pass
    return removed


def build_filename_index(db_root: Path) -> dict[str, Path]:
    idx: dict[str, Path] = {}
    if not db_root.exists():
        return idx
    exts = {".jpg", ".jpeg", ".png", ".bmp"}
    for p in db_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            idx[p.name] = p
    return idx


def rewrite_links_in_text(text: str, name_to_path: dict[str, Path], base_dir: Path, repo_root: Path) -> str:
    # Rewrite any markdown image link whose basename is known in DB to the DB-relative path
    # Allow spaces in the URL inside parentheses (common in doc names) and rebuild with
    # angle brackets around URL when it contains spaces or non-ASCII for broader preview support.
    # Note: this simple pattern does not parse optional titles.
    # Support both plain and angle-bracketed URLs. Angle-bracket form may contain ')'.
    pattern = re.compile(r"!\[([^\]]*)\]\((?:<([^>]+)>|([^)]+))\)")
    exts = {".jpg", ".jpeg", ".png", ".bmp"}

    def repl(m: re.Match) -> str:
        alt = m.group(1)
        old_path = (m.group(2) or m.group(3) or "")
        fname = os.path.basename(old_path)
        if os.path.splitext(fname)[1].lower() not in exts:
            return m.group(0)
        p = name_to_path.get(fname)
        if not p:
            return m.group(0)
        rel = os.path.relpath(str(p), str(base_dir)).replace("\\", "/")
        # If URL has spaces or non-ASCII, wrap in angle brackets to satisfy strict renderers
        needs_brackets = any(ord(ch) > 127 for ch in rel) or (" " in rel)
        url_part = f"(<{rel}>)" if needs_brackets else f"({rel})"
        return f"![{alt}]{url_part}"

    return pattern.sub(repl, text)


def strip_md_images(text: str) -> str:
    # Optionally remove inline image tags to avoid duplicates
    return re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)


def ensure_flat_mineru_images(repo_root: Path) -> int:
    """Ensure a flattened copy of MinerU images exists at:
    outputs/_mineru_tmp/<doc_name>/images/<basename>
    Returns number of files copied.
    """
    src_root = repo_root / "outputs" / "_mineru_tmp"
    copied = 0
    if not src_root.exists():
        return 0
    exts = {".jpg", ".jpeg", ".png", ".bmp"}
    for images_dir in src_root.rglob("auto/images"):
        if not images_dir.is_dir():
            continue
        try:
            rel = images_dir.relative_to(src_root)
            doc_name = rel.parts[0]
        except Exception:
            continue
        flat_dir = src_root / doc_name / "images"
        ensure_dir(flat_dir)
        for src in images_dir.rglob("*"):
            if src.is_file() and src.suffix.lower() in exts:
                dst = flat_dir / src.name
                if not dst.exists():
                    try:
                        shutil.copy2(src, dst)
                        copied += 1
                    except Exception:
                        pass
    return copied


def build_flat_mineru_index(repo_root: Path) -> dict[str, Path]:
    idx: dict[str, Path] = {}
    base = repo_root / "outputs" / "_mineru_tmp"
    exts = {".jpg", ".jpeg", ".png", ".bmp"}
    if not base.exists():
        return idx
    for p in base.rglob("images/*"):
        if p.is_file() and p.suffix.lower() in exts:
            idx[p.name] = p
    return idx


def fix_outputs(repo_root: Path) -> dict:
    out_dir = repo_root / "outputs"
    db_root = repo_root / "qs_image_DB"
    db_idx = build_filename_index(db_root)
    # Ensure flattened MinerU images and build its index
    ensure_flat_mineru_images(repo_root)
    mineru_idx = build_flat_mineru_index(repo_root)
    changed = {"md": False, "tex": False}
    # Fix worksheet.md
    md_path = out_dir / "worksheet.md"
    if md_path.exists():
        txt = md_path.read_text(encoding="utf-8")
        # Rewrite worksheet.md to point to outputs/_mineru_tmp/<doc>/images/<basename>
        new_txt = rewrite_links_in_text(txt, mineru_idx, md_path.parent, repo_root)
        if new_txt != txt:
            md_path.write_text(new_txt, encoding="utf-8")
            changed["md"] = True
    # Fix worksheet.tex
    tex_path = out_dir / "worksheet.tex"
    if tex_path.exists():
        txt = tex_path.read_text(encoding="utf-8")
        new_txt = rewrite_links_in_text(txt, db_idx, tex_path.parent, repo_root)
        if new_txt != txt:
            tex_path.write_text(new_txt, encoding="utf-8")
            changed["tex"] = True
    return changed


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    copied = sync_mineru_tmp_to_db(repo_root)
    removed = cleanup_non_image_in_db(repo_root)
    changed = fix_outputs(repo_root)
    print(f"[sync] copied {copied} images into qs_image_DB, removed {removed} non-images")
    print(f"[links] md_changed={changed['md']} tex_changed={changed['tex']}")


if __name__ == "__main__":
    main()
