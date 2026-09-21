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


def sanitize_path_segment(value: str) -> str:
    cleaned = INVALID_PATH_CHARS.sub("_", value).strip().strip(".")
    return cleaned or "Uncategorized"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def merge_rows(paths: list[Path], overrides: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}

    for path in paths:
        for row in read_csv(path):
            lcsc = (row.get("LCSC") or "").strip().upper()
            if not lcsc:
                continue

            result = merged.setdefault(lcsc, dict(row))
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

            override = overrides.get(lcsc, {})
            if override.get("Category"):
                result["Category"] = override["Category"]
            if override.get("Notes"):
                existing_notes = (result.get("Notes") or "").strip()
                override_note = override["Notes"]
                if override_note not in existing_notes:
                    result["Notes"] = (
                        f"{existing_notes}; {override_note}".strip("; ")
                    )
            if result.get("ReviewStatus") in {"LOOKUP_FAILED", "LCSC_CONFLICT"}:
                result["ReviewStatus"] = "CLASSIFIED_PARTIAL"

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
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    overrides: dict[str, dict[str, str]] = {}
    if args.overrides:
        overrides = {
            (row.get("LCSC") or "").strip().upper(): row
            for row in read_csv(args.overrides.resolve())
            if (row.get("LCSC") or "").strip()
        }

    rows = merge_rows([path.resolve() for path in args.inputs], overrides)
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

    all_fields = list(rows[0].keys())
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
