One-click RAG generation

Files:
- `run_build_rag_dataset.bat` — Windows double-click batch: runs `build_rag_dataset.py` with default args and opens the CSV.
- `run_build_rag_dataset.ps1` — PowerShell runnable equivalent (right-click -> Run with PowerShell).

Behavior:
- Both scripts run `scripts/rag/build_rag_dataset.py --root . --out scripts/data/file_summaries_rag.csv --one-line --max-chars 1000`.
- The `.bat` checks for `python` in PATH and will show the last 5 lines then open the CSV.
- The `.ps1` does the same and exits with the script exit code on failure.

If you prefer different defaults (extensions, max chars), tell me and I can update the scripts to your preferred values.