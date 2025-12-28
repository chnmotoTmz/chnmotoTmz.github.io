@echo off
REM One-click RAG dataset generator (Windows .bat)
REM Double-click this file to generate RAG CSV at scripts\data\file_summaries_rag.csv

set SCRIPT_DIR=%~dp0
where python >nul 2>&1
if errorlevel 1 (
  echo Python not found in PATH. Please ensure Python is installed and on PATH.
  pause
  exit /b 1
)







echo Running build_rag_dataset.py...
python "%SCRIPT_DIR%build_rag_dataset.py" --root "%SCRIPT_DIR%..\.." --out "%SCRIPT_DIR%..\data\file_summaries_rag.csv" --exts .md,.txt,.py,.json --one-line --max-chars 300
if %errorlevel% neq 0 (
  echo ERROR: build_rag_dataset failed with %errorlevel%
  pause
  exit /b %errorlevel%
)
echo Done. Showing last 5 lines:
powershell -NoProfile -Command "Get-Content '%SCRIPT_DIR%..\data\file_summaries_rag.csv' -Tail 5 | ForEach-Object { Write-Host $_ }"
start "" "%SCRIPT_DIR%..\data\file_summaries_rag.csv"

pause
