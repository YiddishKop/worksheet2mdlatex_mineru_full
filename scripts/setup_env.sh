#!/usr/bin/env bash
set -Eeuo pipefail

# [ worksheet2mdlatex ] 环境自动配置脚本（Ubuntu / Bash 版）
# 作用：为 MinerU + pix2tex + OCR 准备独立 Python 环境及依赖

# 切到项目根目录（脚本所在目录的上一层）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================================"
echo "[ 环境自动配置：MinerU + pix2tex + OCR 全依赖 ]"
echo "======================================================"

# 查找 Python 并校验 3.10+
find_python() {
  local candidate
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" - <<'PY' >/dev/null 2>&1; then
import sys
major, minor = sys.version_info[:2]
sys.exit(0 if (major, minor) >= (3, 10) else 1)
PY
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

# 创建并激活虚拟环境
VENV_DIR="venv310"
if [[ ! -d "$VENV_DIR" ]]; then
  echo "🛠️ 创建虚拟环境 $VENV_DIR ..."
  if ! "$PYTHON_BIN" -m venv "$VENV_DIR"; then
    echo "❌ 创建虚拟环境失败。Ubuntu/Debian 可先安装: sudo apt-get update && sudo apt-get install -y python3-venv"
    exit 1
  fi
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# 升级 pip 基础工具
python -m pip install --upgrade pip setuptools wheel -q

# 安装 requirements（使用清华源）
echo "🧩 安装核心依赖中..."
if [[ -f requirements.txt ]]; then
  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
else
  echo "ℹ️ 未找到 requirements.txt，跳过该步骤"
fi

# 关键版本校准（Torch CPU 2.5.1 + dill 0.3.4 + paddlenlp 2.6.1 + mineru 2.6.2）
echo "🧩 对齐 PyTorch CPU 2.5.1 及相关依赖版本 ..."
pip uninstall -y torch torchaudio >/dev/null 2>&1 || true

# === 关键版本校准：Torch/Torchvision/Torchaudio 三件套 ===
echo "🧩 对齐 PyTorch 三件套（自动选择 CUDA 或 CPU）..."
pip uninstall -y torch torchvision torchaudio >/dev/null 2>&1 || true

PIP_TIMEOUT="${PIP_TIMEOUT:-300}"
# 选 CUDA 还是 CPU
if command -v nvidia-smi >/dev/null 2>&1; then
  CUDA_TAG="${CUDA_TAG:-cu121}"  # 如需 cu122，可导出 CUDA_TAG=cu122 后再跑
  TORCH_IDX="https://download.pytorch.org/whl/${CUDA_TAG}"
  echo "➡️ 检测到 NVIDIA GPU，安装 CUDA 轮子: ${CUDA_TAG}"
  if ! pip --default-timeout "$PIP_TIMEOUT" install \
      --index-url "$TORCH_IDX" \
      torch==2.5.1+${CUDA_TAG} torchvision==0.20.1+${CUDA_TAG} torchaudio==2.5.1+${CUDA_TAG}; then
    echo "⚠️ CUDA 轮子安装失败，尝试 CPU 轮子兜底（性能较差）"
    pip --default-timeout "$PIP_TIMEOUT" install \
      --index-url https://download.pytorch.org/whl/cpu \
      torch==2.5.1+cpu torchvision==0.20.1+cpu torchaudio==2.5.1+cpu
  fi
else
  echo "ℹ️ 未检测到 GPU，安装 CPU 轮子"
  pip --default-timeout "$PIP_TIMEOUT" install \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.5.1+cpu torchvision==0.20.1+cpu torchaudio==2.5.1+cpu
fi

# 其他依赖（可以继续用你原来的镜像重试逻辑）
# ---- Torch/Torchvision 健诊（安装完成立刻检测）----
python - <<'PY' || { echo "[ERROR] Torch/Torchvision 校验失败"; exit 10; }
import torch, torchvision
print("torch:", torch.__version__, "torchvision:", torchvision.__version__)
try:
    from torchvision.ops import nms
    ok = True
except Exception as e:
    print("import nms failed:", e)
    ok = False
if torch.cuda.is_available():
    print("CUDA:", torch.version.cuda, "device:", torch.cuda.get_device_name(0))
print("sanity:", ok)
assert ok
PY

# ---- Hugging Face 镜像与缓存（初始化阶段设置）----
: "${HF_ENDPOINT:=https://hf-mirror.com}"
: "${HF_HUB_CACHE:=${HOME}/.cache/huggingface}"
: "${HF_HUB_READ_TIMEOUT:=300}"
export HF_ENDPOINT HF_HUB_CACHE HF_HUB_READ_TIMEOUT

# 安装 CLI 和可选加速插件（存在即跳过）
python - <<'PY' || pip install -q "huggingface_hub[cli]" || true
import importlib, sys
sys.exit(0 if importlib.util.find_spec("huggingface_hub") else 1)
PY
python - <<'PY' || pip install -q hf_transfer || true
import importlib, sys
sys.exit(0 if importlib.util.find_spec("hf_transfer") else 1)
PY

# 如果有 hf_transfer 就启用加速
if python - <<'PY'; then export HF_HUB_ENABLE_HF_TRANSFER=1; else export HF_HUB_ENABLE_HF_TRANSFER=0; fi
import importlib, sys
sys.exit(0 if importlib.util.find_spec("hf_transfer") else 1)
PY

# 预下载 MinerU 常用权重（首次时间较长；失败不致命）
echo "[INFO] Pre-fetch MinerU weights from HF (mirror: $HF_ENDPOINT) ..."
if ! hf download opendatalab/PDF-Extract-Kit-1.0 \
      --repo-type model \
      --local-dir "${HF_HUB_CACHE}/opendatalab__PDF-Extract-Kit-1.0" \
      --include "models/MFD/YOLO/*" "models/Layout/*" "models/OCR/*" "models/Formula/*"; then
  echo "[WARN] Pre-fetch failed (network). Will try online at runtime."
fi


pip install "dill==0.3.4"
pip install "paddlenlp==2.6.1" "mineru==2.6.2"

# 逐项补装/验证（pip 包名 -> import 名称）
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
sys.exit(0 if importlib.util.find_spec("${mod}") else 1)
PY
  then
    echo "⚙️ 自动补装 ${pkg} ..."
    pip install "${pkg}" -i https://pypi.tuna.tsinghua.edu.cn/simple
  else
    echo "✅ ${pkg} 已安装（import ${mod} 正常）"
  fi
done

echo "------------------------------------------------------"
echo "✅ 环境配置完成！"
echo "🔍 使用方式："
echo " source ${VENV_DIR}/bin/activate"
echo " # 然后运行你的项目脚本/命令"
echo "------------------------------------------------------"
