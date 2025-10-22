@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPTDIR=%~dp0"
for %%I in ("%SCRIPTDIR%..") do set "ROOT=%%~fI"

REM Convert outputs\worksheet.md to LaTeX and PDF via Pandoc
set "IN=%ROOT%\outputs\worksheet.md"
set "OUTTEX=%ROOT%\outputs\worksheet_pandoc.tex"
set "OUTPDF=%ROOT%\outputs\worksheet_pandoc.pdf"

if not exist "%IN%" (
  echo ERROR: %IN% not found.
  exit /b 1
)

echo [1/3] Generating %OUTTEX% from %IN% ...
set "LUAFILTER=%SCRIPTDIR%filters\unicode_to_tex.lua"
set "FILTER_ARG="
if exist "%LUAFILTER%" set "FILTER_ARG=--lua-filter=%LUAFILTER%"
pandoc "%IN%" -o "%OUTTEX%" -f gfm -t latex --standalone -V documentclass=article -V geometry:margin=2cm ^
  %FILTER_ARG% ^
  -V mainfont="SimSun" -V CJKmainfont="SimSun" -V mathfont="XITS Math" || goto :err

echo [2/3] Cleaning pandoc-bounded wrappers in %OUTTEX% ...
python "%SCRIPTDIR%clean_pandocbounded.py" "%OUTTEX%" || goto :err

echo [2.2/3] Normalizing LaTeX math delimiters in %OUTTEX% ...
python "%SCRIPTDIR%fix_math_delimiters.py" "%OUTTEX%" || goto :err

echo [2.3/3] Stripping empty enumerate blocks ...
python "%SCRIPTDIR%strip_empty_enumerate.py" "%OUTTEX%" || goto :err

echo [2.5/3] Ensuring XeCJK fonts for Chinese in %OUTTEX% ...
python "%SCRIPTDIR%ensure_cjk_in_tex.py" "%OUTTEX%" || goto :err

echo [2.6/3] Injecting unicode mappings (e.g., triangle -> \triangle) ...
python "%SCRIPTDIR%ensure_unicode_mappings.py" "%OUTTEX%" || goto :err

echo [3/3] Building PDF from cleaned TeX via XeLaTeX ...
if exist "%OUTPDF%" del /q "%OUTPDF%" >nul 2>nul
where xelatex >nul 2>nul && (
  xelatex -interaction=nonstopmode -output-directory="%ROOT%\outputs" "%OUTTEX%" >nul 2>nul || goto :err
) || (
  echo XeLaTeX not found. Falling back to Pandoc PDF...
  pandoc "%IN%" -o "%OUTPDF%" -f gfm --pdf-engine=xelatex -V geometry:margin=2cm -V mainfont="SimSun" -V CJKmainfont="SimSun" -V mathfont="XITS Math" ^
    || pandoc "%IN%" -o "%OUTPDF%" -f gfm --pdf-engine=xelatex -V geometry:margin=2cm -V CJKmainfont="Microsoft YaHei" -V mathfont="XITS Math" ^
    || goto :err
)

echo Done. Wrote:
echo   %OUTTEX%
if exist "%OUTPDF%" echo   %OUTPDF%
exit /b 0

:err
echo Build failed.
exit /b 2
