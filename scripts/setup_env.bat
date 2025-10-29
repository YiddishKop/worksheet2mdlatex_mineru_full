@echo off
chcp 65001 >nul
title [ worksheet2mdlatex ] 环境自动配置脚本
cd /d "%~dp0.."
echo ======================================================
echo [ 环境自动配置：MinerU + pix2tex + OCR 全依赖 ]
echo ======================================================

REM 检查 Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 未检测到 Python，请先安装 3.10+ 版本。
    pause
    exit /b
)

REM 创建虚拟环境
if not exist venv310 (
    echo 🛠️ 创建虚拟环境 venv310...
    python -m venv venv310
)
call venv310\Scripts\activate

REM 升级 pip
python -m pip install --upgrade pip setuptools wheel -q

REM 安装所有依赖
echo 🧩 安装核心依赖中...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

REM 关键版本校准，避免依赖冲突（Torch CPU 2.5.1 + dill 0.3.4 + paddlenlp 2.6.1 + mineru 2.6.2）
echo 🧩 对齐 PyTorch CPU 2.5.1 及相关依赖版本 ...
pip uninstall -y torch torchaudio >nul 2>nul
pip install --index-url https://download.pytorch.org/whl/cpu torch==2.5.1+cpu torchaudio==2.5.1+cpu
pip install "dill==0.3.4"
pip install "paddlenlp==2.6.1" "mineru==2.6.2"

REM 核心依赖补充检查
set packages=torch paddleocr mineru doclayout-yolo ultralytics pix2tex paddlenlp ftfy shapely pyclipper omegaconf onnx pypdfium2 transformers dill
for %%p in (%packages%) do (
    python -c "import %%p" 2>nul
    if errorlevel 1 (
        echo ⚙️ 自动补装 %%p ...
        pip install %%p -i https://pypi.tuna.tsinghua.edu.cn/simple
    ) else (
        echo ✅ %%p 已安装
    )
)

echo ------------------------------------------------------
echo ✅ 环境配置完成！
echo 🔍 现在你可以运行：
echo     scripts\run_mineru_auto.bat
echo     scripts\run_pix2tex_single.bat
echo ------------------------------------------------------
pause
