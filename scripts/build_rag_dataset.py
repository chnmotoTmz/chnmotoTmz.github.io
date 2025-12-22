#!/usr/bin/env python3
"""Build a simple RAG dataset CSV mapping file path -> one_line_summary.

Usage:
  python scripts/build_rag_dataset.py --root . --out data/file_summaries.csv

This script scans files under --root, extracts a short one-line summary for each
text-like file, and writes a CSV with headers: path,one_line_summary
"""

import argparse
import csv
import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_EXTS = {'.md', '.txt', '.py', '.html', '.json', '.csv'}
# File extensions that are considered source code and may be embedded fully when requested
CODE_EXTS = {'.py', '.js', '.ts', '.java', '.sh', '.ps1'}
EXCLUDE_DIRS = {'.git', 'venv', '__pycache__', 'node_modules', 'data', 'pgadmin', 'postgres'}


def guess_summary_from_text(text: str, max_len: int = 200) -> str:
    # Prefer docstrings / comment lines / Markdown headers and avoid picking code lines
    # 1) Triple-quoted docstring (Python-style) anywhere near the top
    import re

    triple_re = re.compile(r'^[ \t]*([ruRU]{0,2})(["\']{3})(.*?)\2', re.S | re.M)
    m = triple_re.search(text)
    if m:
        body = m.group(3).strip()
        for line in body.splitlines():
            s = line.strip()
            if s:
                return s[:max_len]

    # 2) Prefer Markdown header (lines beginning with #) or HTML comment
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith('#'):
            # header text without leading # and trimmed
            header = s.lstrip('#').strip()
            if header:
                return header[:max_len]
        if s.startswith('<!--'):
            # HTML comment
            comment = s.strip('<!-->').strip()
            if comment:
                return comment[:max_len]

    # 3) Prefer comment lines that look like human-readable descriptions
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith('#') or s.startswith('//') or s.startswith('--'):
            # remove comment leader
            cleaned = re.sub(r'^[#\/+\-]+\s*', '', s)
            if len(cleaned) > 10:
                return cleaned[:max_len]

    # 4) Fallback: choose the first non-code-like line (avoid import/def/class/shebang)
    code_prefix_re = re.compile(r'^(#!|import\s+|from\s+|def\s+|class\s+|return\b|if\b|for\b|while\b|except\b|@|\$|console\.log|printf\b)', re.I)
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if len(s) < 8:
            continue
        if code_prefix_re.match(s):
            continue
        # skip lines that look like paths or are mostly punctuation
        if re.match(r'^[\w\-\./\\:]+$', s):
            continue
        return ' '.join(s.split())[:max_len]

    # 5) Last resort: collapse document start
    s = ' '.join(text.split())
    return s[:max_len] if s else ''


def read_file_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding='cp932')
        except Exception as e:
            logger.warning(f"Failed to read {path} due to encoding: {e}")
            return ''
    except Exception as e:
        logger.warning(f"Failed to read {path}: {e}")
        return ''


def build_dataset(root: Path, out_csv: Path, exts: set[str], embed_code: bool = False, one_line: bool = False, max_chars: int = 2000):
    rows = []
    root = root.resolve()

    for dirpath, dirnames, filenames in os.walk(root):
        # skip excluded dirs
        parts = set(Path(dirpath).parts)
        if parts & EXCLUDE_DIRS:
            continue

        for fn in filenames:
            p = Path(dirpath) / fn
            if not p.is_file():
                continue
            if p.suffix.lower() not in exts:
                continue

            rel = p.relative_to(root)
            text = read_file_text(p)
            if not text:
                continue

            if one_line:
                # Collapse entire file into a single line and trim to max_chars
                collapsed = ' '.join(text.split())
                content_to_write = collapsed if max_chars == 0 else collapsed[:max_chars]
            else:
                # If requested, embed full source code for code-like files
                if embed_code and p.suffix.lower() in CODE_EXTS:
                    content_to_write = text
                else:
                    content_to_write = guess_summary_from_text(text)

            if not content_to_write:
                continue

            rows.append({'path': str(rel).replace('\\', '/'), 'one_line_summary': content_to_write})

    # Ensure output dir exists
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    with out_csv.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['path', 'one_line_summary'])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    logger.info(f"Wrote {len(rows)} rows to {out_csv}")
    return len(rows)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=str, default='.', help='Root directory to scan')
    parser.add_argument('--out', type=str, default='data/file_summaries.csv', help='Output CSV path')
    parser.add_argument('--exts', type=str, default=','.join(sorted(DEFAULT_EXTS)), help='Comma-separated file extensions to include')
    parser.add_argument('--embed-code', action='store_true', help='Embed full source code for code file extensions into CSV')
    parser.add_argument('--one-line', action='store_true', help='Collapse whole file content into a single-line summary')
    parser.add_argument('--max-chars', type=int, default=2000, help='Max characters for one-line summary (0 for no limit)')

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s')

    root = Path(args.root)
    out = Path(args.out)
    exts = {e if e.startswith('.') else f'.{e}' for e in args.exts.split(',') if e}

    count = build_dataset(root, out, exts, embed_code=args.embed_code, one_line=args.one_line, max_chars=args.max_chars)
    print(f"Rows: {count}")


if __name__ == '__main__':
    main()
