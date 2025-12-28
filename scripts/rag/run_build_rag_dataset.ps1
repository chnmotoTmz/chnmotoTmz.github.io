# One-click RAG dataset generator (PowerShell)
# Double-click this file in Explorer (right-click -> Run with PowerShell) to generate RAG CSV at scripts/data/file_summaries_rag.csv

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $scriptDir '..')

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Error "python not found in PATH. Please install Python and add it to PATH."
  exit 1
}

Write-Host "Running build_rag_dataset.py..."
python .\scripts\rag\build_rag_dataset.py --root . --out scripts/data/file_summaries_rag.csv --exts .md,.txt,.py,.json --one-line --max-chars 300
if ($LASTEXITCODE -ne 0) {
  Write-Error "build_rag_dataset failed ($LASTEXITCODE)"
  exit $LASTEXITCODE
}

Write-Host "Done. Last 5 lines of output:"
Get-Content scripts/data/file_summaries_rag.csv -Tail 5 | ForEach-Object { Write-Host $_ }
Start-Process scripts/data/file_summaries_rag.csv
