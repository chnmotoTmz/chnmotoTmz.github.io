#!/usr/bin/env python3
"""Utility: convert files to a single-line version by removing newlines.
Usage:
  python scripts/convert_to_oneline.py <file_or_dir> [--out-suffix .oneline]

This writes a new file alongside the original with the given suffix.
"""
import argparse
import sys
from pathlib import Path

def convert_file_to_oneline_content(src: Path) -> str:
    """Return one-line collapsed content for a file."""
    text = src.read_text(encoding='utf-8', errors='ignore')
    # Replace CRLF/CR/LF with single space and collapse multiple spaces
    return ' '.join(text.split())


def write_csv(rows: list[dict], out_csv: Path):
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    import csv
    with out_csv.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['path', 'size_bytes', 'mtime_iso', 'content'])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('paths', nargs='*', help='Files or directories to convert (defaults to current working directory when omitted)')
    parser.add_argument('--out-suffix', default='.oneline', help='Suffix appended to filename if writing individual files (ignored by default)')
    parser.add_argument('--max-size-mb', type=float, default=5.0, help='Skip files larger than this size (MB)')
    parser.add_argument('--write-oneline', action='store_true', help='Write .oneline files instead of producing CSV')
    parser.add_argument('--output-csv', default='scripts/data/oneline_contents.csv', help='When not writing .oneline files, write all output to this CSV')
    args = parser.parse_args(argv)

    paths = args.paths or [str(Path.cwd())]
    out_suffix = args.out_suffix
    max_size = int(args.max_size_mb * 1024 * 1024)
    write_oneline = args.write_oneline
    output_csv = Path(args.output_csv)

    EXCLUDE_DIRS = {'.git', 'venv', '__pycache__', 'node_modules', 'data', 'pgadmin', 'postgres'}

    rows = []
    written = []
    skipped = []

    for p in paths:
        path = Path(p)
        if not path.exists():
            print(f"Skipped: {p} (not found)", file=sys.stderr)
            skipped.append(p)
            continue

        if path.is_dir():
            for f in path.rglob('*'):
                if not f.is_file():
                    continue
                # Skip excluded directories
                if set(f.parts) & EXCLUDE_DIRS:
                    skipped.append(str(f))
                    continue
                # Skip .oneline files themselves
                if f.name.endswith('.oneline'):
                    skipped.append(str(f))
                    continue
                # Skip large files
                try:
                    if f.stat().st_size > max_size:
                        skipped.append(str(f))
                        continue
                except Exception:
                    skipped.append(str(f))
                    continue
                # Quick binary check (NUL byte)
                try:
                    with f.open('rb') as fh:
                        sample = fh.read(4096)
                        if b'\0' in sample:
                            skipped.append(str(f))
                            continue
                except Exception:
                    skipped.append(str(f))
                    continue

                content = convert_file_to_oneline_content(f)
                if write_oneline:
                    out = f.with_name(f.name + out_suffix)
                    out.write_text(content, encoding='utf-8')
                    written.append(str(out))
                    print(f'Wrote: {out}')
                else:
                    rows.append({'path': str(f.relative_to(Path.cwd())).replace('\\','/'), 'size_bytes': f.stat().st_size, 'mtime_iso': f.stat().st_mtime and __import__('datetime').datetime.fromtimestamp(f.stat().st_mtime).isoformat(), 'content': content})

        elif path.is_file():
            f = path
            if f.name.endswith('.oneline'):
                print(f"Skipped existing oneline file: {f}")
                skipped.append(str(f))
                continue
            try:
                if f.stat().st_size > max_size:
                    skipped.append(str(f))
                    continue
            except Exception:
                skipped.append(str(f))
                continue
            try:
                with f.open('rb') as fh:
                    if b'\0' in fh.read(4096):
                        skipped.append(str(f))
                        continue
            except Exception:
                skipped.append(str(f))
                continue

            content = convert_file_to_oneline_content(f)
            if write_oneline:
                out = f.with_name(f.name + out_suffix)
                out.write_text(content, encoding='utf-8')
                written.append(str(out))
                print(f'Wrote: {out}')
            else:
                rows.append({'path': str(f.relative_to(Path.cwd())).replace('\\','/'), 'size_bytes': f.stat().st_size, 'mtime_iso': f.stat().st_mtime and __import__('datetime').datetime.fromtimestamp(f.stat().st_mtime).isoformat(), 'content': content})

    if not write_oneline:
        write_csv(rows, output_csv)
        print(f"Wrote CSV: {output_csv} ({len(rows)} rows)")
    else:
        print(f"Summary: wrote {len(written)} files, skipped {len(skipped)} files")

if __name__ == '__main__':
    main()
