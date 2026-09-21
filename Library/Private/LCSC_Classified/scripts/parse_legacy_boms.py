#!/usr/bin/env python3
"""Parse and normalize legacy JLC paste BOM files into LCSC review CSVs."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import xlrd


LCSC_PATTERN = re.compile(r"C\d+")
PARTS_FIELDS = (
    "LCSC",
    "MPN",
    "Manufacturer",
    "Description",
    "Category",
    "Symbol",
    "Footprint",
    "Value",
    "Package",
    "Datasheet",
    "Model3D",
    "Lifecycle",
    "Source",
    "SourceFootprint",
    "LCSC_URL",
    "Specifications",
    "Notes",
    "ReviewStatus",
)


def normalize(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def designator_count(value: str) -> int:
    return len([item for item in value.split(",") if item.strip()])


def parse_bom(path: Path) -> list[dict[str, object]]:
    workbook = xlrd.open_workbook(path)
    worksheet = workbook.sheet_by_index(0)
    rows: list[dict[str, object]] = []

    for row_index in range(1, worksheet.nrows):
        values = [normalize(worksheet.cell_value(row_index, column)) for column in range(4)]
        comment, package, designator, lcsc_raw = values
        lcsc = lcsc_raw.upper()
        if not LCSC_PATTERN.fullmatch(lcsc):
            continue

        rows.append(
            {
                "source_file": path.name,
                "source_row": row_index + 1,
                "comment": comment,
                "package": package,
                "designator": designator,
                "quantity": designator_count(designator),
                "lcsc": lcsc,
            }
        )

    return rows


def build_review_rows(rows: list[dict[str, object]]) -> tuple[list[dict[str, str]], list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["lcsc"])].append(row)

    review_rows: list[dict[str, str]] = []
    comment_variants: list[dict[str, object]] = []

    for lcsc, group in sorted(grouped.items()):
        variants = {
            (str(row["comment"]), str(row["package"]))
            for row in group
        }
        if len(variants) > 1:
            comment_variants.append(
                {
                    "lcsc": lcsc,
                    "variants": [
                        {
                            "source_file": row["source_file"],
                            "source_row": row["source_row"],
                            "comment": row["comment"],
                            "package": row["package"],
                            "designator": row["designator"],
                        }
                        for row in group
                    ],
                }
            )

        first = group[0]
        source_files = sorted({str(row["source_file"]) for row in group})
        designators = "; ".join(
            f"{row['source_file']}: {row['designator']}" for row in group
        )

        review_rows.append(
            {
                "LCSC": lcsc,
                "MPN": "",
                "Manufacturer": "",
                "Description": "Imported from legacy JLC paste BOM",
                "Category": "",
                "Symbol": "",
                "Footprint": "",
                "Value": str(first["comment"]),
                "Package": str(first["package"]),
                "Datasheet": "",
                "Model3D": "",
                "Lifecycle": "Unknown",
                "Source": "LCSC",
                "SourceFootprint": str(first["package"]),
                "LCSC_URL": f"https://www.lcsc.com/product-detail/{lcsc}.html",
                "Specifications": "",
                "Notes": f"Sources: {', '.join(source_files)}; Designators: {designators}",
                "ReviewStatus": "PENDING_ENRICHMENT",
            }
        )

    return review_rows, comment_variants


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bom_rows: list[dict[str, object]] = []
    for source in sorted(source_dir.glob("*.xls")):
        bom_rows.extend(parse_bom(source))

    if not bom_rows:
        raise RuntimeError(f"No LCSC rows found in {source_dir}")

    review_rows, comment_variants = build_review_rows(bom_rows)

    with (output_dir / "bom_lines.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(bom_rows[0].keys()))
        writer.writeheader()
        writer.writerows(bom_rows)

    with (output_dir / "parts_review.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=PARTS_FIELDS)
        writer.writeheader()
        writer.writerows(review_rows)

    report = {
        "source_files": sorted({str(row["source_file"]) for row in bom_rows}),
        "bom_lines": len(bom_rows),
        "unique_lcsc": len(review_rows),
        "comment_variants": comment_variants,
    }
    (output_dir / "import_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"Parsed {len(bom_rows)} BOM lines, "
        f"{len(review_rows)} unique LCSC parts, "
        f"{len(comment_variants)} comment variants."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
