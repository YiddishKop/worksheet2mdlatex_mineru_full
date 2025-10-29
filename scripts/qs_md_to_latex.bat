@echo off
setlocal
chcp 65001 >nul
title worksheet2mdlatex - qs_DB/*.md -> *.latex

REM Always run from repo root
cd /d "%~dp0.."
echo ======================================================
echo [ worksheet2mdlatex ] Convert qs_DB/*.md to *.latex (manual step)
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

REM 4) Convert qs_DB Markdown parts to LaTeX
REM    Forward any user-provided args to the Python module (e.g., --dir, --file, --mode v2)
if "%*"=="" (
    echo [INFO] Running: python -m scripts.manual_md_to_latex
    python -m scripts.manual_md_to_latex || goto :fail
) else (
    echo [INFO] Running: python -m scripts.manual_md_to_latex %*
    python -m scripts.manual_md_to_latex %* || goto :fail
)

echo ------------------------------------------------------
echo Done. See:
echo   qs_DB\^<doc^>\*.latex
echo (Use --dir or --file to limit scope. Use --mode v2 to skip v1.)
echo ------------------------------------------------------
pause
exit /b 0

:fail
echo ------------------------------------------------------
echo [ERROR] Conversion failed. See messages above.
echo ------------------------------------------------------
pause
exit /b 10

