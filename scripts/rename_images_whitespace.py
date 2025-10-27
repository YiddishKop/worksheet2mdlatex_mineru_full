from __future__ import annotations
from pathlib import Path
import sys


def rename_under_images(images_dir: Path) -> int:
    if not images_dir.exists():
        print(f"[rename-images] skip: not found {images_dir}")
        return 0

    # Collect paths sorted by descending depth so children rename before parents
    items = sorted(images_dir.rglob('*'), key=lambda p: len(p.parts), reverse=True)
    renames = 0
    for p in items:
        try:
            rel_parts = list(p.relative_to(images_dir).parts)
        except ValueError:
            # not under images, skip
            continue

        new_parts = [part.replace(' ', '_') for part in rel_parts]
        if new_parts == rel_parts:
            continue

        dst = images_dir.joinpath(*new_parts)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            # Collision: skip and warn
            print(f"[rename-images][warn] target exists, skip: {p} -> {dst}")
            continue
        print(f"[rename-images] {p} -> {dst}")
        p.rename(dst)
        renames += 1

    print(f"[rename-images] done, renamed={renames}")
    return renames


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    images_dir = repo / 'images'
    rename_under_images(images_dir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

