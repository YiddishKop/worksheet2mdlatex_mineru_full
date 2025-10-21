from pathlib import Path
import re
import platform
import subprocess


def ensure_dir(p: Path) -> None:
    """确保目录存在（若不存在则递归创建）。"""
    p.mkdir(parents=True, exist_ok=True)


# 常见题号样式正则片段（供其他模块参考）
QUESTION_NUMBER_PATTERNS = [
    r"(?:例|练习)\s*\d+",
    r"\b\d+\s*[\.、)]",
    r"\(\d+\)",
    r"[（(]\s*\d+\s*[）)]",
]


def has_likely_options(text: str) -> bool:
    """粗判文本中是否包含 A/B/C/D 选择题选项标记。

    例如："A.", "B)", "C、" 等。
    """
    return bool(re.search(r"\b[ABCD]\s*[\.、)]", text))


def split_options(text: str):
    """将题干中的 A-D 选项拆分为 [(标签, 文案)] 列表。

    若无法可靠切分，则返回 None。
    """
    parts = re.split(r"\b([ABCD]\s*[\.、)])", text)
    if len(parts) < 3:
        return None
    items = []
    cur = None
    buf = []
    for p in parts:
        if re.fullmatch(r"[ABCD]\s*[\.、)]", p or ""):
            if cur:
                items.append((cur, "".join(buf).strip()))
            cur = p.strip()
            buf = []
        else:
            buf.append(p)
    if cur:
        items.append((cur, "".join(buf).strip()))
    return items if items else None


def detect_gpu_type() -> str:
    """检测本机 GPU 类型。

    返回：
    - 'nvidia' | 'amd' | 'none'
    """
    sys = platform.system().lower()
    try:
        if sys == 'windows':
            out = subprocess.check_output(
                "wmic path win32_VideoController get name",
                shell=True, text=True
            ).lower()
        else:
            out = subprocess.check_output(
                "lspci | grep -i vga",
                shell=True, text=True
            ).lower()
        if 'nvidia' in out:
            return 'nvidia'
        if 'amd' in out or 'radeon' in out:
            return 'amd'
    except Exception:
        pass
    return 'none'

