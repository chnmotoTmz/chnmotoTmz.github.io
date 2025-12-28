#!/usr/bin/env python3
"""Filter merged oneline CSV to remove unwanted paths (e.g., cache data).
Usage:
  python scripts/filter_oneline_merged.py --in scripts/data/oneline_merged.csv --out scripts/data/oneline_merged.cleaned.csv
"""
import argparse
import csv
from pathlib import Path

DEFAULT_PATTERNS = ["cache/hatena_content/"]


def filter_csv(input_csv: Path, output_csv: Path, patterns: list[str]):
    kept = 0
    removed = 0
    with input_csv.open('r', encoding='utf-8') as inf, output_csv.open('w', encoding='utf-8', newline='') as outf:
        reader = csv.DictReader(inf)
        writer = csv.DictWriter(outf, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in reader:
            path = row.get('path','')
            if any(path.startswith(p) for p in patterns):
                removed += 1
                continue
            writer.writerow(row)
            kept += 1
    print(f"Wrote {kept} rows to {output_csv} (removed {removed} rows)")
    return kept, removed


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--in', dest='input', default='scripts/data/oneline_merged.csv')
    parser.add_argument('--out', dest='output', default='scripts/data/oneline_merged.cleaned.csv')
    parser.add_argument('--pattern', dest='patterns', action='append', help='Prefix pattern to exclude (can be given multiple times)')
    args = parser.parse_args(argv)

    patterns = args.patterns or DEFAULT_PATTERNS
    input_csv = Path(args.input)
    output_csv = Path(args.output)
    filter_csv(input_csv, output_csv, patterns)

if __name__ == '__main__':
    main()
