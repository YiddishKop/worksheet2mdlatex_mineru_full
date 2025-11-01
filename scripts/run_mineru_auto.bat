@echo off
setlocal
chcp 65001 >nul
title worksheet2mdlatex - MinerU (auto run)

REM Always run from repo root
cd /d "%~dp0.."
echo ======================================================
echo [ worksheet2mdlatex MinerU AUTO RUN ]
echo ======================================================

REM Step 1: Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python not found. Please install Python 3.10+:
    echo https://www.python.org/downloads/release/python-31011/
    pause
    exit /b 1
)

REM Step 2: Ensure venv exists
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

REM Step 3: Activate venv
call venv310\Scripts\activate
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate venv310. Check path.
    pause
    exit /b 3
)

REM Step 4: Ensure MinerU package in current venv (CLI comes from venv)
echo [INFO] Ensuring MinerU is installed in this venv ...
python -c "import mineru" >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Installing MinerU + deps into venv ...
    pip install mineru doclayout-yolo paddlenlp pypdfium2 onnx==1.16.0 || goto :fail
)

REM Step 5: Ensure outputs dir
if not exist outputs mkdir outputs

REM Step 5.5: Preprocess image/file names (spaces -> underscores)
echo [INFO] Normalizing image names in images\ (spaces -> underscores) ...
python -m scripts.rename_images_whitespace || goto :fail

REM Step 6: Run MinerU pipeline (robust)
echo [INFO] Running MinerU pipeline ...
python -m src.pipeline --images_dir images --out_dir outputs --format both --use_mineru
if %errorlevel% neq 0 (
    if exist outputs\worksheet.md (
        echo [WARN] MinerU pipeline returned rc=%errorlevel%, continuing with existing outputs\worksheet.md
    ) else (
        echo [ERROR] MinerU pipeline failed and no outputs\worksheet.md present.
        goto :fail
    )
)

REM Step 6.5: Normalize question titles (merge number + stem into one line)
echo [INFO] Normalizing question titles in outputs\worksheet.md ...
python -m scripts.normalize_md_question_titles || goto :fail

REM Step 6.6: Insert linebreaks before '??:' / '??<n>:'
echo [INFO] Inserting linebreaks before ??/??<n> ...
python -m scripts.insert_linebreaks_before_solutions || goto :fail

REM Step 7: Sync image DB and fix links
echo [INFO] Sync images to qs_image_DB and fix links ...
python -m scripts.sync_qs_image_db_and_fix_links || goto :fail

REM Step 7.5: Split worksheet.md into parts for later processing
echo [INFO] Splitting worksheet.md into qs_DB parts ...
python -m scripts.split_md_to_parts || goto :fail

REM Step 7.6: Run v1 + v2 on qs_DB/*.md to produce .latex per question
echo [INFO] Converting qs_DB/*.md to .latex via v1+v2 ...
python -m scripts.batch_v1_v2_to_latex || goto :fail

REM Step 8: Regenerate Pandoc TeX/PDF after link fix
echo [INFO] Regenerating Pandoc TeX/PDF from corrected worksheet.md ...
call scripts\pandoc_export.bat

echo ------------------------------------------------------
echo Done. Files under outputs\ :
echo   outputs\worksheet.md
if exist outputs\worksheet.tex echo   outputs\worksheet.tex
echo   outputs\worksheet_pandoc.tex
if exist outputs\worksheet_pandoc.pdf echo   outputs\worksheet_pandoc.pdf
echo ------------------------------------------------------
pause
exit /b 0

:fail
echo ------------------------------------------------------
echo [ERROR] Pipeline failed. See messages above.
echo To diagnose, run: scripts\check_env.bat
echo ------------------------------------------------------
pause
exit /b 10


