import sys
from pathlib import Path

def main():
    if len(sys.argv) < 3:
        print("usage: make_utf8_bom_copy.py <src> <dst>")
        sys.exit(2)
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    text = src.read_text(encoding='utf-8', errors='strict')
    # utf-8-sig writes BOM
    dst.write_text(text, encoding='utf-8-sig')

if __name__ == '__main__':
    main()

