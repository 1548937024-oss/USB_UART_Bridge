#!/usr/bin/env python3
"""Synchronize symbol metadata from the classified LCSC master table."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from library_metadata import clean, iter_symbol_libraries, update_symbol_library_metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts_csv", type=Path)
    parser.add_argument("--library-root", type=Path, required=True)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing symbol libraries.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    parts_csv = args.parts_csv.resolve()
    library_root = args.library_root.resolve()

    with parts_csv.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    rows_by_lcsc = {
        clean(row.get("LCSC")).upper(): row
        for row in rows
        if clean(row.get("LCSC"))
    }

    if not library_root.is_dir():
        raise FileNotFoundError(f"Library root does not exist: {library_root}")

    changed_files = 0
    changed_symbols = 0
    for symbol_library in iter_symbol_libraries(library_root):
        if args.dry_run:
            original = symbol_library.read_text(encoding="utf-8")
            temporary = symbol_library.with_suffix(".kicad_sym.sync")
            temporary.write_text(original, encoding="utf-8")
            try:
                count = update_symbol_library_metadata(temporary, rows_by_lcsc)
                changed = temporary.read_text(encoding="utf-8") != original
            finally:
                temporary.unlink(missing_ok=True)
        else:
            count = update_symbol_library_metadata(symbol_library, rows_by_lcsc)
            changed = count > 0

        if changed:
            changed_files += 1
            changed_symbols += count
            print(f"{symbol_library}: {count} symbol(s)")

    action = "Would update" if args.dry_run else "Updated"
    print(f"{action} {changed_symbols} symbol(s) in {changed_files} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
