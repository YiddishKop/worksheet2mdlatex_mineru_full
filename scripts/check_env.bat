@echo off
title worksheet2mdlatex - 环境检查
cd /d "%~dp0.."
echo ============================================================
echo [ 环境检测工具 - worksheet2mdlatex ]
echo ============================================================

echo.
echo [Python 环境]
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 未检测到 python，请先安装 Python 3.10+
) else (
    python --version
    python -m pip --version
)

echo.
echo [PIP 依赖检测]
python -m pip freeze > _pip_list.txt
for %%p in (pillow pytesseract paddleocr pix2tex mineru requests) do (
    findstr /i "%%p" _pip_list.txt >nul
    if errorlevel 1 (
        echo ❌ 缺少 %%p，请执行: pip install %%p
    ) else (
        echo ✅ %%p 已安装
    )
)
del _pip_list.txt >nul 2>nul

echo.
echo [Tesseract OCR 检查]
where tesseract >nul 2>nul
if %errorlevel% neq 0 (
    echo ⚠️  未找到 tesseract.exe，请确认已安装或配置到 PATH。
) else (
    tesseract --version | findstr /i "tesseract"
)

echo.
echo [GPU 检测]
python - <<EOF
import subprocess, platform
import re
print("系统:", platform.system(), platform.release())
try:
    if platform.system().lower()=="windows":
        out=subprocess.check_output("wmic path win32_VideoController get name", shell=True, text=True)
    else:
        out=subprocess.check_output("lspci | grep -i vga", shell=True, text=True)
    low=out.lower()
    if "nvidia" in low: print("✅ 检测到 NVIDIA GPU")
    elif "amd" in low or "radeon" in low: print("✅ 检测到 AMD GPU")
    else: print("🧠 未检测到独立 GPU，默认使用 CPU")
except Exception as e:
    print("⚠️ 无法检测 GPU：", e)
EOF

echo.
echo [MinerU 检测]
mineru --version 2>nul
if %errorlevel% neq 0 (
    echo ❌ MinerU 未安装或命令未识别，请执行: pip install mineru
) else (
    echo ✅ MinerU 命令可用
)

echo.
echo [pix2tex 检测]
python -m pix2tex.cli --help >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ pix2tex 未安装或命令不可用
) else (
    echo ✅ pix2tex 模块可用
)

echo.
echo [PaddleOCR 模型检查]
python - <<EOF
try:
    from paddleocr import PaddleOCR
    print("✅ PaddleOCR 模块可导入")
except Exception as e:
    print("⚠️ PaddleOCR 未安装或配置异常：", e)
EOF

echo.
echo [MathPix API 检测 (.env)]
python - <<EOF
import os
from dotenv import load_dotenv
load_dotenv()
aid=os.getenv("MATHPIX_APP_ID")
akey=os.getenv("MATHPIX_APP_KEY")
if not (aid and akey):
    print("⚠️ .env 中未检测到 MATHPIX_APP_ID / KEY")
else:
    print("✅ 已检测到 MathPix 凭证（未验证有效性）")
EOF

echo.
echo ============================================================
echo ✅ 环境检测完成！如有 ❌ 或 ⚠️ 提示，请按提示安装或配置。
echo ============================================================
pause
