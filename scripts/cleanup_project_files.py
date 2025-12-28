#!/usr/bin/env python3
"""
Project File Cleanup Script
Based on the file necessity judgment report, this script performs the following actions:
- Deletes files marked as "削除可" (deletable)
- Moves files marked as "アーカイブ検討" (archive consideration) to an archive directory
- Leaves files marked as "維持" (maintain) untouched

Usage: python scripts/cleanup_project_files.py [--dry-run] [--archive-dir scripts/archive]
"""

import argparse
import os
import shutil
from pathlib import Path

# Files to delete (削除可)
FILES_TO_DELETE = [
    "advanced_ollama_test.py",
    "check_setup_complete.py",
    "debug_hatena_blogs.py",
    "practical_test.py",
    "run_with_debug_logs.py",
    "test_blogselector_comprehensive.py",
    "test_blogselector_fix.py",
    "test_blog_selector.py",
    "test_blog_selector_debug.py",
    "test_chrome_api.py",
    "test_command_parser.py",
    "test_csv.py",
    "test_custom_api.py",
    "test_custom_api_folder_monitor.py",
    "test_custom_api_image.py",
    "test_exclude_keywords.py",
    "test_groq_service.py",
    "test_prompt_logging.py",
    "test_prompt_logging_simple.py",
    "test_rag_content_fetcher.py",
    "test_rag_summary.py",
    "test_signature.py",
    "test_v2_structure.py",
    "test_webhook_flow.py",
    "test_webhook_gemini.py",
    "test_webhook_simple.py",
    "file_list.txt",
    "scripts/rag/build_rag_dataset.oneline.py",
    "scripts/rag/redaction_report.txt",
    "scripts/rag/redaction_report_v2.txt",
    "src/tasks/chat_history_manager_task.py",
]

# Files to archive (アーカイブ検討)
FILES_TO_ARCHIVE = [
    "app.py",
    "run_app.py",
    "demo_tasks.py",
    "scripts/check_claude_models.py",
    "scripts/check_encoding.py",
    "scripts/detect_encoding.py",
    "scripts/run_claude_service_unit_checks.py",
    "scripts/run_registry_check.py",
]

# Files to maintain (維持) - do nothing
FILES_TO_MAINTAIN = [
    "scripts/cleanup_oneline_files.py",
    "scripts/convert_to_oneline.py",
    "scripts/convert_to_utf8.py",
    "scripts/create_tables.py",
    "scripts/filter_oneline_merged.py",
    "scripts/merge_oneline_to_csv.py",
    "scripts/rag/build_rag_dataset.py",
    "scripts/rag/README.md",
]

def main():
    parser = argparse.ArgumentParser(description="Cleanup project files based on necessity report")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
    parser.add_argument("--archive-dir", default="scripts/archive", help="Directory to move archive files to")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]  # Assuming script is in scripts/
    archive_dir = repo_root / args.archive_dir

    if not args.dry_run:
        archive_dir.mkdir(parents=True, exist_ok=True)

    print("Project File Cleanup Script")
    print("=" * 50)
    print(f"Dry run: {args.dry_run}")
    print(f"Archive directory: {archive_dir}")
    print()

    # Delete files
    print("Deleting files marked as '削除可' (deletable):")
    for file_path in FILES_TO_DELETE:
        full_path = repo_root / file_path
        if full_path.exists():
            if args.dry_run:
                print(f"  Would delete: {file_path}")
            else:
                try:
                    if full_path.is_file():
                        full_path.unlink()
                    else:
                        shutil.rmtree(full_path)
                    print(f"  Deleted: {file_path}")
                except Exception as e:
                    print(f"  Error deleting {file_path}: {e}")
        else:
            print(f"  Not found: {file_path}")

    print()

    # Archive files
    print("Archiving files marked as 'アーカイブ検討' (archive consideration):")
    for file_path in FILES_TO_ARCHIVE:
        full_path = repo_root / file_path
        archive_path = archive_dir / file_path
        if full_path.exists():
            if args.dry_run:
                print(f"  Would move: {file_path} -> {archive_path}")
            else:
                try:
                    archive_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(full_path), str(archive_path))
                    print(f"  Moved: {file_path} -> {archive_path}")
                except Exception as e:
                    print(f"  Error moving {file_path}: {e}")
        else:
            print(f"  Not found: {file_path}")

    print()

    # Maintain files - just list them
    print("Maintaining files marked as '維持' (maintain) - no action taken:")
    for file_path in FILES_TO_MAINTAIN:
        full_path = repo_root / file_path
        if full_path.exists():
            print(f"  Keeping: {file_path}")
        else:
            print(f"  Not found (but keeping anyway): {file_path}")

    print()
    print("Cleanup complete!")

if __name__ == "__main__":
    main()