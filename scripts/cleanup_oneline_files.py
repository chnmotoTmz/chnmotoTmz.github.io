#!/usr/bin/env python3
"""Backup and delete all '.oneline' files under the repo.
Usage:
  python scripts/cleanup_oneline_files.py --root . --backup-dir scripts/oneline_backup --dry-run

By default this will move files into the backup dir preserving relative paths (so originals are removed).
Use --dry-run to see what would be moved.
"""
import argparse
from pathlib import Path
import shutil
from datetime import datetime

EXCLUDE_DIRS = {'.git', 'venv', '__pycache__', 'node_modules'}


def find_oneline(root: Path):
    for p in root.rglob('*.oneline'):
        if not p.is_file():
            continue
        if set(p.parts) & EXCLUDE_DIRS:
            continue
        yield p


def backup_and_remove(root: Path, backup_dir: Path, dry_run: bool = False):
    root = root.resolve()
    backup_dir = backup_dir.resolve()
    moved = 0
    for p in find_oneline(root):
        # Skip anything that is already in the backup dir (avoid recursive moves)
        try:
            if backup_dir == p.resolve() or backup_dir in p.resolve().parents:
                # already in backup -> skip
                continue
        except Exception:
            # if resolve fails for weird paths, skip moving that path
            continue

        rel = p.relative_to(root)
        dest = backup_dir / rel
        if dry_run:
            print(f"Would move: {p} -> {dest}")
            moved += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(dest))
        moved += 1
    return moved


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.', help='Root to search')
    parser.add_argument('--backup-dir', default=f'scripts/oneline_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}', help='Where to move .oneline files')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)

    root = Path(args.root)
    backup_dir = Path(args.backup_dir)
    moved = backup_and_remove(root, backup_dir, dry_run=args.dry_run)
    if args.dry_run:
        print(f"Dry-run: {moved} matching files would be moved to {backup_dir}")
    else:
        print(f"Moved {moved} files to {backup_dir}")

if __name__ == '__main__':
    main()
