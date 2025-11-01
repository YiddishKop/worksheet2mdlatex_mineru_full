#!/usr/bin/env bash
set -Eeuo pipefail

[ worksheet2mdlatex ] 环境自动配置脚本（Ubuntu / Bash 版）
切到项目根目录（脚本所在目录的上一层）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================================"
echo "[ 环境自动配置：MinerU + pix2tex + OCR 全依赖 ]"
echo "======================================================"

查找 Python 并校验 3.10+
find_python() {
local candidate
for candidate in python3 python; do
if command -v "$candidate" >/dev/null 2>&1; then
if "$candidate" - <<'PY' >/dev/null 2>&1; then
import sys
major, minor = sys.version_info[:2]
sys.exit(0 if (major, minor) >= (3, 10) else 1)
PY
then
echo "$candidate"
return 0
fi
fi
done
return 1
}

if ! PYTHON_BIN="$(find_python)"; then
echo "❌ 未检测到 Python 3.10+，请先安装（建议 python3.10 或以上）。"
exit 1
fi
echo "✅ 使用 Python: $PYTHON_BIN ($($PYTHON_BIN -V))"

创建并激活虚拟环境
VENV_DIR="venv310"
if [[ ! -d "$VENV_DIR" ]]; then
echo "🛠️ 创建虚拟环境 $VENV_DIR ..."
if ! "$PYTHON_BIN" -m venv "$VENV_DIR"; then
echo "❌ 创建虚拟环境失败。Ubuntu/Debian 可先安装: sudo apt-get update && sudo apt-get install -y python3-venv"
exit 1
fi
fi

shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

升级 pip 基础工具
python -m pip install --upgrade pip setuptools wheel -q

安装 requirements（使用清华源）
echo "🧩 安装核心依赖中..."
if [[ -f requirements.txt ]]; then
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
else
echo "ℹ️ 未找到 requirements.txt，跳过该步骤"
fi

关键版本校准（Torch CPU 2.5.1 + dill 0.3.4 + paddlenlp 2.6.1 + mineru 2.6.2）
echo "🧩 对齐 PyTorch CPU 2.5.1 及相关依赖版本 ..."
pip uninstall -y torch torchaudio >/dev/null 2>&1 || true
pip install --index-url https://download.pytorch.org/whl/cpu torch==2.5.1+cpu torchaudio==2.5.1+cpu
pip install "dill==0.3.4"
pip install "paddlenlp==2.6.1" "mineru==2.6.2"

逐项补装/验证（pip 包名 -> import 名称）
declare -A PKG_TO_IMPORT=(
[torch]=torch
[paddleocr]=paddleocr
[mineru]=mineru
[doclayout-yolo]=doclayout_yolo
[ultralytics]=ultralytics
[pix2tex]=pix2tex
[paddlenlp]=paddlenlp
[ftfy]=ftfy
[shapely]=shapely
[pyclipper]=pyclipper
[omegaconf]=omegaconf
[onnx]=onnx
[pypdfium2]=pypdfium2
[transformers]=transformers
[dill]=dill
)
for pkg in "${!PKG_TO_IMPORT[@]}"; do
mod="${PKG_TO_IMPORT[$pkg]}"
if ! python - <<PY 2>/dev/null
import importlib, sys
sys.exit(0 if importlib.util.find_spec("$mod") else 1)
PY
then
echo "⚙️ 自动补装 $pkg ..."
pip install "$pkg" -i https://pypi.tuna.tsinghua.edu.cn/simple
else
echo "✅ $pkg 已安装（import $mod 正常）"
fi
done

echo "------------------------------------------------------"
echo "✅ 环境配置完成！"
echo "🔍 使用方式："
echo " source $VENV_DIR/bin/activate"
echo " # 然后运行你的项目脚本/命令"
echo "------------------------------------------------------"