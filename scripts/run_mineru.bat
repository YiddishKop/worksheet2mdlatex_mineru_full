@echo off
title worksheet2mdlatex (MinerU mode)
cd /d "%~dp0.."
echo [INFO] Working dir: %CD%
if not exist outputs mkdir outputs
python -m src.pipeline --images_dir images --out_dir outputs --format both --use_mineru
if %ERRORLEVEL% neq 0 (
  echo [ERROR] MinerU mode failed. Press any key to exit...
  pause >nul
  exit /b %ERRORLEVEL%
)
echo.
echo [OK] Done! See outputs\ folder.
echo.
pause
