import os
import shutil
import argparse
from pathlib import Path

def clean_mineru_output(base_dir, dry_run=False):
    """
    Cleans up MinerU output directories.
    Retains only .md files and 'images' folder.
    Deletes everything else in the leaf directories containing .md files.
    """
    base_path = Path(base_dir)
    if not base_path.exists():
        print(f"Error: Directory '{base_dir}' does not exist.")
        return

    print(f"Scanning '{base_dir}' for cleanup...")
    print(f"Dry run: {'ON' if dry_run else 'OFF'}")

    # Walk bottom-up to handle nested structures safely
    for root, dirs, files in os.walk(base_dir, topdown=False):
        root_path = Path(root)
        
        # Check if this directory contains any .md files
        has_md = any(f.endswith('.md') for f in files)
        
        if has_md:
            print(f"\nProcessing: {root_path}")
            
            # 1. DELETE FILES
            for file in files:
                file_path = root_path / file
                if not file.endswith('.md'):
                    if dry_run:
                        print(f"  [Would Delete] File: {file}")
                    else:
                        try:
                            file_path.unlink()
                            print(f"  [Deleted] File: {file}")
                        except Exception as e:
                            print(f"  [Error] Deleting {file}: {e}")
                else:
                    if dry_run:
                        # print(f"  [Keep] {file}")
                        pass

            # 2. DELETE DIRECTORIES
            for d in dirs:
                dir_path = root_path / d
                if d != 'images':
                    if dry_run:
                        print(f"  [Would Delete] Dir:  {d}")
                    else:
                        try:
                            shutil.rmtree(dir_path)
                            print(f"  [Deleted] Dir:  {d}")
                        except Exception as e:
                            print(f"  [Error] Deleting directory {d}: {e}")
                else:
                    if dry_run:
                        # print(f"  [Keep] Dir: {d}")
                        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up MinerU output, keeping only .md and images.")
    parser.add_argument("--dir", default="outputs/_mineru_tmp", help="Base directory to clean (default: outputs/_mineru_tmp)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be deleted without actually deleting")
    
    args = parser.parse_args()
    
    clean_mineru_output(args.dir, args.dry_run)
