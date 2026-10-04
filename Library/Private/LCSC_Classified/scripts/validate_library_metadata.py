#!/usr/bin/env python3
"""Validate datasheet and identity metadata across the classified LCSC library."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

from library_metadata import (
    clean,
    extract_top_level_blocks,
    is_partial,
    is_pdf_reference,
    iter_symbol_libraries,
    property_value,
)


SYMBOL_METADATA_FIELDS = (
    "Datasheet",
    "DatasheetRev",
    "DatasheetDate",
    "LocalDatasheet",
    "Manufacturer",
    "MPN",
    "LCSC Part",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts_csv", type=Path)
    parser.add_argument("--library-root", type=Path, required=True)
    parser.add_argument("--library-index", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as a validation failure.",
    )
    return parser.parse_args()


def issue(
    severity: str,
    lcsc: str,
    code: str,
    message: str,
) -> dict[str, str]:
    return {
        "severity": severity,
        "lcsc": lcsc,
        "code": code,
        "message": message,
    }


def scan_symbol_metadata(
    library_root: Path,
) -> tuple[dict[str, dict[str, str]], list[dict[str, str]]]:
    symbols: dict[str, dict[str, str]] = {}
    issues: list[dict[str, str]] = []

    for symbol_library in iter_symbol_libraries(library_root):
        text = symbol_library.read_text(encoding="utf-8")
        for block in extract_top_level_blocks(text):
            lcsc = clean(property_value(block, "LCSC Part")).upper()
            if not lcsc:
                continue

            metadata = {
                field: clean(property_value(block, field))
                for field in SYMBOL_METADATA_FIELDS
            }
            metadata["Value"] = clean(property_value(block, "Value"))
            metadata["LibraryFile"] = str(symbol_library)
            if lcsc in symbols:
                issues.append(
                    issue(
                        "error",
                        lcsc,
                        "DUPLICATE_SYMBOL",
                        f"Symbol appears in both {symbols[lcsc]['LibraryFile']} "
                        f"and {symbol_library}.",
                    )
                )
                continue
            symbols[lcsc] = metadata

    return symbols, issues


def local_path_exists(value: str, relative_to: Path) -> bool:
    if not value or re.search(r"\$\{[^}]+\}", value):
        return True
    path = Path(value)
    if not path.is_absolute():
        path = relative_to / path
    return path.is_file()


def validate() -> int:
    args = parse_args()
    parts_csv = args.parts_csv.resolve()
    library_root = args.library_root.resolve()

    with parts_csv.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if args.library_index:
        with args.library_index.open(newline="", encoding="utf-8-sig") as handle:
            index_rows = list(csv.DictReader(handle))
        index_by_lcsc = {
            clean(row.get("LCSC")).upper(): row
            for row in index_rows
            if clean(row.get("LCSC"))
        }
        for row in rows:
            index_row = index_by_lcsc.get(clean(row.get("LCSC")).upper())
            if index_row:
                row["ConversionStatus"] = index_row.get("ConversionStatus", "")

    symbols, issues = scan_symbol_metadata(library_root)
    status_counts: Counter[str] = Counter()
    review_counts: Counter[str] = Counter()
    conversion_counts: Counter[str] = Counter()

    for row in rows:
        lcsc = clean(row.get("LCSC")).upper()
        if not lcsc:
            issues.append(issue("error", "", "MISSING_LCSC", "A row has no LCSC key."))
            continue

        partial = is_partial(row)
        datasheet = clean(row.get("Datasheet"))
        local_datasheet = clean(row.get("LocalDatasheet"))
        datasheet_status = (
            "PDF"
            if is_pdf_reference(datasheet) or is_pdf_reference(local_datasheet)
            else "MISSING"
            if not datasheet and not local_datasheet
            else "NOT_PDF"
        )
        status_counts[datasheet_status] += 1
        review_counts[clean(row.get("ReviewStatus")) or "(blank)"] += 1
        conversion_counts[clean(row.get("ConversionStatus")) or "(blank)"] += 1

        if datasheet and not is_pdf_reference(datasheet):
            issues.append(
                issue(
                    "error",
                    lcsc,
                    "DATASHEET_NOT_PDF",
                    f"Datasheet must reference a PDF: {datasheet}",
                )
            )
        if local_datasheet and not local_path_exists(
            local_datasheet,
            parts_csv.parent,
        ):
            issues.append(
                issue(
                    "error",
                    lcsc,
                    "LOCAL_DATASHEET_MISSING",
                    f"LocalDatasheet does not exist: {local_datasheet}",
                )
            )

        if not partial and datasheet_status != "PDF":
            issues.append(
                issue(
                    "error",
                    lcsc,
                    "DATASHEET_MISSING",
                    "Verified part has no PDF datasheet.",
                )
            )
        elif partial and datasheet_status != "PDF":
            issues.append(
                issue(
                    "warning",
                    lcsc,
                    "PARTIAL_DATASHEET_MISSING",
                    "Partial or placeholder part still needs a verified PDF datasheet.",
                )
            )

        if not partial:
            if not clean(row.get("MPN")):
                issues.append(
                    issue("error", lcsc, "MPN_MISSING", "Verified part has no MPN.")
                )
            if not clean(row.get("Manufacturer")):
                issues.append(
                    issue(
                        "error",
                        lcsc,
                        "MANUFACTURER_MISSING",
                        "Verified part has no manufacturer.",
                    )
                )

        conversion_status = clean(row.get("ConversionStatus")).upper()
        symbol = symbols.get(lcsc)
        if conversion_status == "CONVERTED" and symbol is None:
            issues.append(
                issue(
                    "error",
                    lcsc,
                    "SYMBOL_MISSING",
                    "Index reports CONVERTED but no KiCad symbol contains this LCSC key.",
                )
            )

        if symbol is None:
            if partial:
                issues.append(
                    issue(
                        "warning",
                        lcsc,
                        "PARTIAL_SYMBOL_MISSING",
                        "Partial or placeholder part has no converted symbol yet.",
                    )
                )
            continue

        for field in SYMBOL_METADATA_FIELDS:
            source_field = "LCSC" if field == "LCSC Part" else field
            source_value = clean(row.get(source_field))
            symbol_value = symbol[field]
            if field == "LCSC Part":
                source_value = source_value.upper()
                symbol_value = symbol_value.upper()
            if source_value != symbol_value:
                issues.append(
                    issue(
                        "error",
                        lcsc,
                        "SYMBOL_METADATA_MISMATCH",
                        f"{field} differs: master={source_value!r}, "
                        f"symbol={symbol_value!r} ({symbol['LibraryFile']}).",
                    )
                )

        category = clean(row.get("Category"))
        if category.startswith(
            ("Resistors/", "Capacitors/", "Inductors, Coils, Chokes/")
        ):
            source_value = clean(row.get("Value"))
            symbol_value = clean(symbol.get("Value"))
            if source_value and symbol_value != source_value:
                issues.append(
                    issue(
                        "error",
                        lcsc,
                        "PASSIVE_VALUE_MISMATCH",
                        f"Value differs: master={source_value!r}, "
                        f"symbol={symbol_value!r} ({symbol['LibraryFile']}).",
                    )
                )

    errors = [item for item in issues if item["severity"] == "error"]
    warnings = [item for item in issues if item["severity"] == "warning"]
    report = {
        "parts": len(rows),
        "symbols": len(symbols),
        "datasheet_status": dict(sorted(status_counts.items())),
        "review_status": dict(sorted(review_counts.items())),
        "conversion_status": dict(sorted(conversion_counts.items())),
        "errors": errors,
        "warnings": warnings,
    }

    if args.report:
        report_path = args.report.resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(
        f"Validated {len(rows)} parts and {len(symbols)} symbols: "
        f"{status_counts.get('PDF', 0)} PDF datasheets, "
        f"{status_counts.get('MISSING', 0)} missing, "
        f"{status_counts.get('NOT_PDF', 0)} not PDF; "
        f"{len(errors)} error(s), {len(warnings)} warning(s)."
    )
    for item in errors[:40]:
        print(f"ERROR {item['lcsc'] or '-'} {item['code']}: {item['message']}")
    for item in warnings[:20]:
        print(f"WARN  {item['lcsc'] or '-'} {item['code']}: {item['message']}")

    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(validate())
