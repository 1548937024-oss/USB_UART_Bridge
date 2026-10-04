#!/usr/bin/env python3
"""Merge LCSC part data and create category-based KiCad library placeholders."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path


INVALID_PATH_CHARS = re.compile(r'[<>:"/\\|?*]+')
PART_FIELDS = (
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
    "DatasheetRev",
    "DatasheetDate",
    "LocalDatasheet",
    "Model3D",
    "Lifecycle",
    "Source",
    "SourceFootprint",
    "LCSC_URL",
    "Specifications",
    "Notes",
    "ReviewStatus",
    "SourceBundles",
)


def sanitize_path_segment(value: str) -> str:
    cleaned = INVALID_PATH_CHARS.sub("_", value).strip().strip(".")
    return cleaned or "Uncategorized"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def append_note(row: dict[str, str], note: str) -> None:
    if not note:
        return
    existing_notes = (row.get("Notes") or "").strip()
    if note not in existing_notes:
        row["Notes"] = f"{existing_notes}; {note}".strip("; ")


def apply_overrides(
    row: dict[str, str],
    category_overrides: dict[str, dict[str, str]],
    metadata_overrides: dict[str, dict[str, str]],
) -> None:
    lcsc = row["LCSC"]
    override = category_overrides.get(lcsc, {})
    if override.get("Category"):
        row["Category"] = override["Category"]
    append_note(row, (override.get("Notes") or "").strip())

    override = metadata_overrides.get(lcsc, {})
    for field, value in override.items():
        if field == "LCSC" or not value:
            continue
        if field == "Notes":
            append_note(row, value)
        else:
            row[field] = value

    if row.get("ReviewStatus") in {"LOOKUP_FAILED", "LCSC_CONFLICT"}:
        row["ReviewStatus"] = "CLASSIFIED_PARTIAL"


def merge_rows(
    paths: list[Path],
    category_overrides: dict[str, dict[str, str]],
    metadata_overrides: dict[str, dict[str, str]],
    excluded: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}

    for path in paths:
        for row in read_csv(path):
            lcsc = (row.get("LCSC") or "").strip().upper()
            if not lcsc:
                continue
            if lcsc in excluded:
                continue

            result = merged.setdefault(
                lcsc,
                {field: "" for field in PART_FIELDS},
            )
            for field in PART_FIELDS:
                if field == "LCSC":
                    continue
                value = (row.get(field) or "").strip()
                if value:
                    result[field] = value
            result["LCSC"] = lcsc

            source_name = path.parent.name
            previous_sources = result.get("SourceBundles", "")
            sources = {
                item.strip()
                for item in previous_sources.split(";")
                if item.strip()
            }
            if source_name != "data":
                sources.add(source_name)
            result["SourceBundles"] = "; ".join(sorted(sources))

    for row in merged.values():
        apply_overrides(row, category_overrides, metadata_overrides)

    return sorted(merged.values(), key=lambda row: row["LCSC"])


def write_empty_symbol_library(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            (
                "(kicad_symbol_lib",
                "  (version 20251024)",
                '  (generator "kicad_symbol_editor")',
                '  (generator_version "10.0")',
                ")",
                "",
            )
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--metadata-overrides", type=Path)
    parser.add_argument("--exclude-parts", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    category_overrides: dict[str, dict[str, str]] = {}
    if args.overrides:
        category_overrides = {
            (row.get("LCSC") or "").strip().upper(): row
            for row in read_csv(args.overrides.resolve())
            if (row.get("LCSC") or "").strip()
        }

    metadata_overrides: dict[str, dict[str, str]] = {}
    if args.metadata_overrides:
        metadata_overrides = {
            (row.get("LCSC") or "").strip().upper(): row
            for row in read_csv(args.metadata_overrides.resolve())
            if (row.get("LCSC") or "").strip()
        }

    excluded: dict[str, dict[str, str]] = {}
    if args.exclude_parts:
        excluded = {
            (row.get("LCSC") or "").strip().upper(): row
            for row in read_csv(args.exclude_parts.resolve())
            if (row.get("LCSC") or "").strip()
        }

    rows = merge_rows(
        [path.resolve() for path in args.inputs],
        category_overrides,
        metadata_overrides,
        excluded,
    )
    if not rows:
        raise RuntimeError("No parts found")

    category_groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    top_counts: dict[str, int] = defaultdict(int)

    for row in rows:
        category = (row.get("Category") or "").strip()
        segments = [segment.strip() for segment in category.split("/") if segment.strip()]
        top = segments[0] if segments else "Uncategorized"
        sub = segments[1] if len(segments) > 1 else "Other"
        category_groups[(top, sub)].append(row)
        top_counts[top] += 1

    data_dir = output_dir / "data"
    category_dir = data_dir / "categories"
    libraries_dir = output_dir / "libraries"
    data_dir.mkdir(parents=True, exist_ok=True)
    libraries_dir.mkdir(parents=True, exist_ok=True)
    if category_dir.exists():
        shutil.rmtree(category_dir)
    category_dir.mkdir(parents=True, exist_ok=True)

    all_fields = list(PART_FIELDS)
    for row in rows:
        for field in row:
            if field not in all_fields:
                all_fields.append(field)
    with (data_dir / "all_parts.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=all_fields)
        writer.writeheader()
        writer.writerows(rows)

    for (top, sub), group in sorted(category_groups.items()):
        top_name = sanitize_path_segment(top)
        sub_name = sanitize_path_segment(sub)
        target_dir = category_dir / top_name / sub_name
        target_dir.mkdir(parents=True, exist_ok=True)
        with (target_dir / "parts.csv").open(
            "w", newline="", encoding="utf-8-sig"
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=all_fields)
            writer.writeheader()
            writer.writerows(group)

    for top in sorted(top_counts):
        top_name = sanitize_path_segment(top)
        library_dir = libraries_dir / top_name
        write_empty_symbol_library(library_dir / f"{top_name}.kicad_sym")
        (library_dir / f"{top_name}.pretty").mkdir(parents=True, exist_ok=True)
        (library_dir / f"{top_name}.3dshapes").mkdir(parents=True, exist_ok=True)

    index = {
        "parts": len(rows),
        "top_categories": dict(sorted(top_counts.items())),
        "category_paths": [
            {
                "top": top,
                "sub": sub,
                "parts": len(group),
            }
            for (top, sub), group in sorted(category_groups.items())
        ],
    }
    (data_dir / "category_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Classified {len(rows)} unique parts into {len(category_groups)} categories.")
    for top, count in sorted(top_counts.items()):
        print(f"  {top}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
