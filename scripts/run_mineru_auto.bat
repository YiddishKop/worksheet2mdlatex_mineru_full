@echo off
chcp 65001 >nul
title worksheet2mdlatex - MinerU 鑷慨澶嶈繍琛屽櫒
cd /d "%~dp0.."
echo ======================================================
echo [ worksheet2mdlatex MinerU 鑷姩杩愯鑴氭湰 ]
echo ======================================================

REM Step 1: 妫€鏌?Python 鏄惁瀛樺湪
echo.
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo 鉂?鏈娴嬪埌 Python锛岃鍏堝畨瑁?Python 3.10 鎴栨洿楂樼増鏈€?
    echo 鍙粠 https://www.python.org/downloads/release/python-31011/ 涓嬭浇銆?
    pause
    exit /b
)

REM Step 2: 妫€鏌ヨ櫄鎷熺幆澧冩槸鍚﹀瓨鍦?
if not exist venv310 (
    echo 鈿狅笍  鏈壘鍒?venv310 铏氭嫙鐜锛屾鍦ㄨ嚜鍔ㄥ垱寤?..
    if exist scripts\setup_env.bat (
        call scripts\setup_env.bat
    ) else (
        echo 鉂?缂哄皯 setup_env.bat锛岃纭椤圭洰瀹屾暣銆?
        pause
        exit /b
    )
)

REM Step 3: 婵€娲昏櫄鎷熺幆澧?
call venv310\Scripts\activate
if %errorlevel% neq 0 (
    echo 鉂?鏃犳硶婵€娲?venv310 鐜锛岃妫€鏌ヨ矾寰勩€?
    pause
    exit /b
)

REM Step 4: 妫€鏌?mineru 鍛戒护鏄惁鍙敤
where mineru >nul 2>nul
if %errorlevel% neq 0 (
    echo 鈿狅笍 MinerU 鍛戒护涓嶅彲鐢紝灏濊瘯閲嶆柊瀹夎...
    pip install mineru doclayout-yolo paddlenlp pypdfium2 onnx==1.16.0
)

REM Step 5: 纭繚杈撳嚭鐩綍瀛樺湪
if not exist outputs mkdir outputs

REM Step 6: 鎵ц MinerU 绠￠亾
echo.
echo [INFO] 鍚姩 MinerU 瑙ｆ瀽娴佺▼...
python -m src.pipeline --images_dir images --out_dir outputs --format both --use_mineru

if %ERRORLEVEL% neq 0 (
    echo ------------------------------------------------------
    echo 鉂?MinerU 杩愯澶辫触锛岃妫€鏌ヤ笂鏂归敊璇俊鎭€?
    echo 寤鸿鎵ц锛歴cripts\check_env.bat 鏌ョ湅鐜鐘舵€併€?
    echo ------------------------------------------------------
    pause
    exit /b %ERRORLEVEL%
)

REM Step 7: Sync image DB and fix links
echo.
echo [INFO] Syncing images to qs_image_DB and fixing links...
python -m scripts.sync_qs_image_db_and_fix_links

echo ------------------------------------------------------
echo Done. Outputs are in outputs\ :
echo   outputs\worksheet.md
echo   outputs\worksheet.tex
echo ------------------------------------------------------
pause
