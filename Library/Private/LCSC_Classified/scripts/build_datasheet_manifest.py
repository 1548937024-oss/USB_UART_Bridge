#!/usr/bin/env python3
"""Build a local datasheet manifest and validate every archived PDF."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parts-csv", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    return parser.parse_args()


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def is_pdf(path: Path) -> bool:
    if not path.is_file():
        return False
    with path.open("rb") as handle:
        return handle.read(4096).lstrip().startswith(b"%PDF")


def main() -> int:
    args = parse_args()
    parts_csv = args.parts_csv.resolve()
    with parts_csv.open(newline="", encoding="utf-8-sig") as handle:
        parts = list(csv.DictReader(handle))

    rows = []
    missing = []
    invalid = []
    for part in parts:
        local = clean(part.get("LocalDatasheet"))
        local_path = (parts_csv.parent / local).resolve() if local else None
        exists = bool(local_path and local_path.is_file())
        pdf_header = bool(local_path and is_pdf(local_path))
        if not exists:
            missing.append(clean(part.get("LCSC")))
        elif not pdf_header:
            invalid.append(clean(part.get("LCSC")))
        rows.append(
            {
                "LCSC": clean(part.get("LCSC")),
                "MPN": clean(part.get("MPN")),
                "Datasheet": clean(part.get("Datasheet")),
                "DatasheetRev": clean(part.get("DatasheetRev")),
                "LocalDatasheet": local,
                "LocalExists": "YES" if exists else "NO",
                "PdfHeader": "YES" if pdf_header else "NO",
                "Status": (
                    "OK"
                    if exists and pdf_header
                    else "INVALID_PDF"
                    if exists
                    else "MISSING"
                ),
            }
        )

    output_csv = args.output_csv.resolve()
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "parts": len(rows),
        "local_datasheets": len(rows) - len(missing) - len(invalid),
        "missing": missing,
        "invalid_pdf": invalid,
    }
    args.output_report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Local datasheets: {report['local_datasheets']}/{report['parts']} valid; "
        f"missing={len(missing)}, invalid={len(invalid)}."
    )
    return 1 if missing or invalid else 0


if __name__ == "__main__":
    raise SystemExit(main())
