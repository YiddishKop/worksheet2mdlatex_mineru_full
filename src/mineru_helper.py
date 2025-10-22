"""
mineru_helper.py
----------------
提供对 MinerU 命令行工具的统一封装：
1) 自动检测 MinerU 版本与 CLI 兼容方式（新版本需要 `-p/--path`）。
2) 按需回退到 `python -m mineru` 调用，提升在不同安装环境中的可用性。
3) 针对 PyTorch 2.6+ 的安全反序列化机制，自动注册 `ultralytics` 模型类型到 `safe_globals`，
   以便 MinerU 依赖的 DocLayout YOLO 等模型能顺利加载。
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import subprocess, json, re, sys

# ----------------------------------------------------------
# 兼容 PyTorch 2.6+ 模型反序列化安全机制
# ----------------------------------------------------------
try:
    import torch  # type: ignore
    import ultralytics  # type: ignore
    from packaging import version  # type: ignore
    if version.parse(torch.__version__) >= version.parse("2.6.0"):
        print(f"[INFO] 检测到 PyTorch {torch.__version__} (>=2.6)，启用 safe_globals 自动补丁")
        torch.serialization.add_safe_globals([
            ultralytics.nn.tasks.DetectionModel  # 供 DocLayout YOLO 反序列化
        ])
except Exception as e:
    print(f"[WARN] PyTorch safe_globals 自动补丁加载失败: {e}")


class MinerUHelper:
    """MinerU CLI 辅助类。

    职责：
    - 读取并缓存 MinerU 版本号，避免重复开销；
    - 根据版本号判断是否使用新版 CLI 语法（是否需要 `-p`）；
    - 封装执行 `mineru parse` 的调用，自动选择备选命令并解析输出结果。
    """

    _cached_version: Optional[str] = None
    _use_new_cli: Optional[bool] = None

    @classmethod
    def get_version(cls) -> str:
        """获取 MinerU 版本号（字符串）。

        优先执行 `mineru --version`；失败则尝试 `python -m mineru --version`。
        结果会缓存在类变量 `_cached_version` 中，后续重复调用直接返回缓存。
        """
        if cls._cached_version:
            return cls._cached_version
        # Prefer the current interpreter (venv) to ensure consistency
        try:
            output = subprocess.check_output([sys.executable, "-m", "mineru", "--version"], text=True, stderr=subprocess.STDOUT)
            cls._cached_version = output.strip()
        except Exception:
            try:
                output = subprocess.check_output(["mineru", "--version"], text=True, stderr=subprocess.STDOUT)
                cls._cached_version = output.strip()
            except Exception:
                cls._cached_version = "unknown"
        return cls._cached_version

    @classmethod
    def is_new_cli(cls) -> bool:
        """判断是否使用“新 CLI”参数格式（是否需要 `-p/--path`）。

        逻辑：解析版本字符串中的主/次版本号：
        - 若主版本 > 0，或次版本 >= 2，则视为新 CLI（需要 `-p`）；
        - 若无法解析版本，则默认按新 CLI 处理以提高兼容性。
        结果将缓存在 `_use_new_cli` 中。
        """
        if cls._use_new_cli is not None:
            return cls._use_new_cli
        version_str = cls.get_version()
        match = re.search(r"([0-9]+)\.([0-9]+)", version_str)
        if match:
            major, minor = map(int, match.groups())
            cls._use_new_cli = (major > 0 or minor >= 2)
        else:
            cls._use_new_cli = True
        return cls._use_new_cli

    @classmethod
    def run_parse(cls, input_path: Path, output_dir: Path) -> Optional[Dict[str, Any]]:
        """执行 MinerU 解析任务并尝试解析输出结果。

        - 按 `is_new_cli()` 自动选择是否添加 `-p` 参数；
        - 依次尝试 `mineru` 与 `python -m mineru` 两种入口；
        - 运行后优先读取 `output_dir` 中的 `*.json`，否则读取 `*.md`；
        - 若无可用输出，返回 None，并在控制台打印告警。

        参数：
        - input_path: 输入的图片或 PDF 路径。
        - output_dir: MinerU 输出目录（若不存在会创建）。

        返回：
        - dict 或 None：解析后的结构化结果或空值。
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        is_new = cls.is_new_cli()
        ver = cls._cached_version or "unknown"
        print(f"[INFO] MinerU 版本检测：{ver} | {'新CLI(-p)' if is_new else '旧CLI'}")

        cmds: List[List[str]]
        if is_new:
            cmds = [
                [sys.executable, "-m", "mineru", "parse", "-p", str(input_path), "--output", str(output_dir)],
                ["mineru", "parse", "-p", str(input_path), "--output", str(output_dir)],
            ]
        else:
            cmds = [
                [sys.executable, "-m", "mineru", "parse", str(input_path), "--output", str(output_dir)],
                ["mineru", "parse", str(input_path), "--output", str(output_dir)],
            ]

        last_err: Optional[Exception] = None
        for cmd in cmds:
            try:
                print(f"[INFO] Running: {' '.join(cmd)}")
                subprocess.check_call(cmd)
                break
            except Exception as e:
                last_err = e

        json_files = sorted(output_dir.glob("*.json"))
        if json_files:
            try:
                return json.loads(json_files[0].read_text(encoding="utf-8"))
            except Exception:
                pass

        md_files = sorted(output_dir.glob("*.md"))
        if md_files:
            return {"blocks": [{"type": "markdown", "text": md_files[0].read_text(encoding="utf-8")}]}

        print("[WARN] MinerU 未产生可解析输出。")
        if last_err:
            print("[DEBUG] 错误详情:", last_err)
        return None

