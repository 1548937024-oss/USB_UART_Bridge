#!/usr/bin/env python3
"""Build an index mapping LCSC parts to their classified KiCad library files."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


INVALID_PATH_CHARS = re.compile(r'[<>:"/\\|?*]+')


def sanitize_path_segment(value: str) -> str:
    return INVALID_PATH_CHARS.sub("_", value).strip().strip(".") or "Uncategorized"


def extract_top_level_blocks(text: str, token: str) -> list[str]:
    starts = list(re.finditer(rf'(?m)^\s*\({re.escape(token)}\s+"', text))
    blocks: list[str] = []

    for match in starts:
        start = match.start() + match.group(0).index("(")
        depth = 0
        in_string = False
        escaped = False

        for index in range(start, len(text)):
            character = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    in_string = False
                continue

            if character == '"':
                in_string = True
            elif character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    blocks.append(text[start : index + 1])
                    break

    return blocks


def property_value(block: str, property_name: str) -> str:
    match = re.search(
        rf'\(property\s+"{re.escape(property_name)}"\s+"([^"]*)"',
        block,
    )
    return match.group(1) if match else ""


def symbol_name(block: str) -> str:
    match = re.search(r'\(symbol\s+"([^"]+)"', block)
    return match.group(1) if match else ""


def model_path(block: str) -> str:
    match = re.search(r'\(model\s+"([^"]+)"', block)
    return match.group(1) if match else ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts_csv", type=Path)
    parser.add_argument("--library-root", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    parts_path = args.parts_csv.resolve()
    library_root = args.library_root.resolve()
    output_csv = args.output_csv.resolve()
    output_report = args.output_report.resolve() if args.output_report else None

    with parts_path.open(newline="", encoding="utf-8-sig") as handle:
        parts = list(csv.DictReader(handle))

    converted: dict[str, dict[str, str]] = {}

    for category_dir in sorted(path for path in library_root.iterdir() if path.is_dir()):
        category_name = category_dir.name
        symbol_libraries = list(category_dir.glob("*.kicad_sym"))
        footprint_libraries = list(category_dir.glob("*.pretty"))

        symbol_library = symbol_libraries[0] if symbol_libraries else None
        footprint_library = footprint_libraries[0] if footprint_libraries else None

        footprint_models: dict[str, str] = {}
        if footprint_library:
            for footprint_file in footprint_library.glob("*.kicad_mod"):
                model = model_path(footprint_file.read_text(encoding="utf-8"))
                if model:
                    footprint_models[footprint_file.stem] = model

        if not symbol_library:
            continue

        for block in extract_top_level_blocks(
            symbol_library.read_text(encoding="utf-8"),
            "symbol",
        ):
            lcsc = property_value(block, "LCSC Part").strip().upper()
            if not lcsc:
                continue

            footprint_ref = property_value(block, "Footprint")
            footprint_name = (
                footprint_ref.split(":", 1)[1]
                if ":" in footprint_ref
                else footprint_ref
            )
            converted[lcsc] = {
                "LibraryCategory": category_name,
                "SymbolLibrary": symbol_library.name,
                "Symbol": symbol_name(block),
                "FootprintLibrary": footprint_library.name if footprint_library else "",
                "Footprint": footprint_name,
                "Model3D": footprint_models.get(footprint_name, ""),
                "ConversionStatus": "CONVERTED",
            }

    output_fields = list(parts[0].keys())
    for field in (
        "LibraryCategory",
        "SymbolLibrary",
        "Symbol",
        "FootprintLibrary",
        "Footprint",
        "Model3D",
        "ConversionStatus",
    ):
        if field not in output_fields:
            output_fields.append(field)

    output_rows: list[dict[str, str]] = []
    converted_count = 0
    for part in parts:
        row = dict(part)
        lcsc = (row.get("LCSC") or "").strip().upper()
        mapping = converted.get(lcsc)
        if mapping:
            converted_count += 1
            row.update(mapping)
        else:
            category = (row.get("Category") or "").strip()
            top = category.split("/", 1)[0].strip()
            row.update(
                {
                    "LibraryCategory": sanitize_path_segment(top),
                    "SymbolLibrary": "",
                    "Symbol": row.get("Symbol", ""),
                    "FootprintLibrary": "",
                    "Footprint": row.get("Footprint", ""),
                    "Model3D": row.get("Model3D", ""),
                    "ConversionStatus": "PENDING_CONVERSION",
                }
            )
        output_rows.append(row)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(output_rows)

    report = {
        "parts": len(output_rows),
        "converted": converted_count,
        "pending_conversion": len(output_rows) - converted_count,
        "converted_by_category": {
            category: sum(
                1
                for row in output_rows
                if row["ConversionStatus"] == "CONVERTED"
                and row["LibraryCategory"] == category
            )
            for category in sorted(
                {
                    row["LibraryCategory"]
                    for row in output_rows
                    if row["ConversionStatus"] == "CONVERTED"
                }
            )
        },
    }

    if output_report:
        output_report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(
        f"Indexed {len(output_rows)} parts: "
        f"{converted_count} converted, "
        f"{len(output_rows) - converted_count} pending."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
