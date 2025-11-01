#!/usr/bin/env bash
set -Eeuo pipefail

# UTF-8 终端标题（可选）
printf '\033]0;%s\007' 'worksheet2mdlatex - To qs_DB MD (no LaTeX)'

# 始终从仓库根目录运行（脚本所在目录的上一层）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "======================================================"
echo "[ worksheet2mdlatex ] MinerU -> qs_DB/*.md (stop before .latex)"
echo "======================================================"

# -------- 1) 检查 Python 3.10+ --------
find_python() {
  local c
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1; then
      if "$c" - <<'PY' >/dev/null 2>&1; then
import sys
sys.exit(0 if sys.version_info >= (3,10) else 1)
PY
        echo "$c"
        return 0
      fi
    fi
  done
  return 1
}

if ! PYTHON_BIN="$(find_python)"; then
  echo "Python not found. Please install Python 3.10+"
  exit 1
fi

# -------- 2) 确保 venv 存在，不在则调用 scripts/setup_env.sh --------
if [[ ! -d "venv310" ]]; then
  echo "[INFO] venv310 missing. Creating via scripts/setup_env.sh ..."
  if [[ -f "scripts/setup_env.sh" ]]; then
    bash "scripts/setup_env.sh" || { echo "[ERROR] setup_env.sh failed"; exit 10; }
  else
    echo "[ERROR] Missing scripts/setup_env.sh. Project incomplete."
    exit 2
  fi
fi

# -------- 3) 激活 venv --------
# shellcheck disable=SC1091
source "venv310/bin/activate" || {
  echo "[ERROR] Failed to activate venv310. Check path."
  exit 3
}

# ---- HF 环境准备（运行期更稳）----
: "${HF_ENDPOINT:=https://hf-mirror.com}"
: "${HF_HUB_CACHE:=${HOME}/.cache/huggingface}"
: "${HF_HUB_READ_TIMEOUT:=300}"
export HF_ENDPOINT HF_HUB_CACHE HF_HUB_READ_TIMEOUT
if python - <<'PY'; then export HF_HUB_ENABLE_HF_TRANSFER=1; else export HF_HUB_ENABLE_HF_TRANSFER=0; fi
import importlib, sys
sys.exit(0 if importlib.util.find_spec("hf_transfer") else 1)
PY

# 若缓存已存在则改为离线模式；否则在线拉取一次
MODEL_DIR="${HF_HUB_CACHE}/opendatalab__PDF-Extract-Kit-1.0/models/MFD/YOLO"
if [[ -d "$MODEL_DIR" ]]; then
  export HF_HUB_OFFLINE=1
else
  echo "[INFO] HF cache missing, trying to fetch YOLO weights online..."
  hf download opendatalab/PDF-Extract-Kit-1.0 \
    --repo-type model \
    --local-dir "${HF_HUB_CACHE}/opendatalab__PDF-Extract-Kit-1.0" \
    --include "models/MFD/YOLO/*" || echo "[WARN] Online fetch failed; MinerU may retry itself."
fi


# -------- 4) 确保 MinerU 在当前 venv 中可用 --------
echo "[INFO] Ensuring MinerU is installed in this venv ..."
if ! python -c "import mineru" >/dev/null 2>&1; then
  echo "[INFO] Installing MinerU + deps into venv ..."
  # 与 .bat 对齐的核心依赖；如需锁版本可在此调整
  if ! pip install mineru doclayout-yolo paddlenlp pypdfium2 onnx==1.16.0; then
    echo "[ERROR] pip install mineru and deps failed"
    exit 10
  fi
fi

# -------- 5) 确保 outputs 目录 --------
mkdir -p outputs

# -------- 5.5) 规范化图片文件名（空格 -> 下划线）--------
echo "[INFO] Normalizing image names in images/ (spaces -> underscores) ..."
if ! python -m scripts.rename_images_whitespace; then
  echo "[ERROR] scripts.rename_images_whitespace failed"
  exit 10
fi

# -------- 6) 跑 MinerU -> 规范化 -> 拆分到 qs_DB（不保留 worksheet.md）--------
#    支持自定义输入根目录作为第一个参数（默认 images）
INPUT_DIR="images"
if [[ "${1:-}" != "" ]]; then
  INPUT_DIR="$1"
fi

echo "[INFO] Running MinerU on ${INPUT_DIR} (recursive PDFs) to produce _mineru_tmp ...."
if ! python -m scripts.run_mineru_only --images_dir "$INPUT_DIR" --out_dir outputs --recursive --only_pdf; then
  echo "[ERROR] scripts.run_mineru_only failed"
  exit 10
fi

echo "[INFO] Normalize + split directly from MinerU auto/*.md ..."
if ! python -m scripts.split_from_mineru_md; then
  echo "[ERROR] scripts.split_from_mineru_md failed"
  exit 10
fi

echo "------------------------------------------------------"
echo "Done. See:"
echo "  qs_DB/<doc>/*.md (split parts)"
echo "  qs_image_DB/<doc>/*.jpg/png (images)"
echo "Next step to produce LaTeX: scripts/qs_md_to_latex.sh"
echo "Tip: You can run this as: scripts/run_to_qs_md.sh  /path/to/pdf_root"
echo "------------------------------------------------------"