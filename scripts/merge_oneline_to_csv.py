#!/usr/bin/env python3
"""Merge all '*.oneline' files into a single CSV.
Columns: path, size_bytes, mtime_iso, content

Usage:
  python scripts/merge_oneline_to_csv.py --root . --out scripts/data/oneline_merged.csv
"""
import argparse
import csv
from pathlib import Path
from datetime import datetime

EXCLUDE_DIRS = {'.git', 'venv', '__pycache__', 'node_modules'}


def find_oneline_files(root: Path):
    for p in root.rglob('*'):
        if not p.is_file():
            continue
        if p.suffix != '.oneline':
            continue
        if set(p.parts) & EXCLUDE_DIRS:
            continue
        yield p


def read_text_safe(path: Path):
    try:
        return path.read_text(encoding='utf-8')
    except Exception:
        try:
            return path.read_text(encoding='cp932')
        except Exception:
            return path.read_text(encoding='utf-8', errors='replace')


def merge(root: Path, out: Path, max_size_mb: float = 50.0):
    rows = []
    root = root.resolve()
    max_bytes = int(max_size_mb * 1024 * 1024)

    for p in find_oneline_files(root):
        try:
            size = p.stat().st_size
        except Exception:
            continue
        if size > max_bytes:
            print(f"Skipping (too large): {p} ({size} bytes)")
            continue
        content = read_text_safe(p)
        mtime = datetime.fromtimestamp(p.stat().st_mtime).isoformat()
        rel = p.relative_to(root)
        rows.append({'path': str(rel).replace('\\','/'), 'size_bytes': size, 'mtime_iso': mtime, 'content': content})

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['path','size_bytes','mtime_iso','content'], quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Wrote {len(rows)} rows to {out} (skipped files > {max_size_mb} MB)")
    return len(rows)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.', help='Root to search')
    parser.add_argument('--out', default='scripts/data/oneline_merged.csv', help='CSV output path')
    parser.add_argument('--max-size-mb', type=float, default=50.0, help='Skip files larger than this size (MB)')
    args = parser.parse_args(argv)

    root = Path(args.root)
    out = Path(args.out)
    merge(root, out, max_size_mb=args.max_size_mb)

if __name__ == '__main__':
    main()
