@echo off
setlocal
chcp 65001 >nul
title worksheet2mdlatex - MinerU (direct split)

REM Always run from repo root
cd /d "%~dp0.."
echo ======================================================
echo [ worksheet2mdlatex MinerU DIRECT SPLIT ]
echo ======================================================

REM 1) Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM 2) Ensure venv exists
if not exist venv310 (
    echo [INFO] venv310 missing. Creating via scripts\setup_env.bat ...
    if exist scripts\setup_env.bat (
        call scripts\setup_env.bat || goto :fail
    ) else (
        echo [ERROR] Missing scripts\setup_env.bat. Project incomplete.
        pause
        exit /b 2
    )
)

REM 3) Activate venv
call venv310\Scripts\activate
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate venv310. Check path.
    pause
    exit /b 3
)

REM 4) Ensure MinerU in this venv
echo [INFO] Ensuring MinerU is installed in this venv ...
python -c "import mineru" >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Installing MinerU + deps into venv ...
    pip install mineru doclayout-yolo paddlenlp pypdfium2 onnx==1.16.0 || goto :fail
)

REM 5) Ensure outputs dir
if not exist outputs mkdir outputs

REM 5.5) Normalize image names (spaces -> underscores)
echo [INFO] Normalizing image names in images\ (spaces -> underscores) ...
python -m scripts.rename_images_whitespace || goto :fail

REM 6) MinerU -> normalize -> split to qs_DB (no worksheet.md persisted)
echo [INFO] Running MinerU to produce _mineru_tmp ....
python -m scripts.run_mineru_only --images_dir images --out_dir outputs || goto :fail
echo [INFO] Normalize + split directly from MinerU auto/*.md ...
python -m scripts.split_from_mineru_md || goto :fail

echo [INFO] Converting qs_DB/*.md to .latex via v1+v2 ...
python -m scripts.batch_v1_v2_to_latex || goto :fail

echo ------------------------------------------------------
echo Done. See:
echo   qs_DB\^<doc^>\*.md (split parts)
echo   qs_image_DB\^<doc^>\*.jpg/png (images)
echo   qs_DB\^<doc^>\*.latex (if v1+v2 ran OK)
echo ------------------------------------------------------
pause
exit /b 0

:fail
echo ------------------------------------------------------
echo [ERROR] Direct split pipeline failed. See messages above.
echo ------------------------------------------------------
pause
exit /b 10




