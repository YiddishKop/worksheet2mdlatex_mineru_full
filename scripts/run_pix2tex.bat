@echo off
title worksheet2mdlatex (pix2tex legacy)
cd /d "%~dp0.."
echo [INFO] Working dir: %CD%
if not exist outputs mkdir outputs
python -m src.pipeline --images_dir images --out_dir outputs --format both --use_pix2tex
if %ERRORLEVEL% neq 0 (
  echo [ERROR] pix2tex mode failed. Press any key to exit...
  pause >nul
  exit /b %ERRORLEVEL%
)
echo.
echo [OK] Done! See outputs\ folder.
echo.
pause
