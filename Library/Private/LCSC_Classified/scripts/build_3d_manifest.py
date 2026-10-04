#!/usr/bin/env python3
"""Build and validate the footprint-to-3D-model manifest."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-index", type=Path, required=True)
    parser.add_argument("--library-root", type=Path, required=True)
    parser.add_argument("--kicad-root", type=Path, default=Path(r"D:\KiCad10.0"))
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    return parser.parse_args()


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def resolve_model(
    model: str,
    library_root: Path,
    kicad_root: Path,
) -> Path | None:
    if model.startswith("${LCSC_LIB_ROOT}/"):
        return (library_root / model[len("${LCSC_LIB_ROOT}/") :]).resolve()
    if model.startswith("${KICAD10_3DMODEL_DIR}/"):
        return (
            kicad_root
            / "share"
            / "kicad"
            / "3dmodels"
            / model[len("${KICAD10_3DMODEL_DIR}/") :]
        ).resolve()
    if model:
        path = Path(model)
        return path.resolve() if path.is_absolute() else None
    return None


def main() -> int:
    args = parse_args()
    with args.library_index.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    output_rows = []
    missing = []
    invalid = []
    for row in rows:
        if clean(row.get("ConversionStatus")).upper() != "CONVERTED":
            continue
        model = clean(row.get("Model3D"))
        resolved = resolve_model(model, args.library_root, args.kicad_root)
        exists = bool(resolved and resolved.is_file())
        status = "OK" if exists else "MISSING" if not model else "INVALID"
        if status == "MISSING":
            missing.append(clean(row.get("LCSC")))
        elif status == "INVALID":
            invalid.append(clean(row.get("LCSC")))
        output_rows.append(
            {
                "LCSC": clean(row.get("LCSC")),
                "MPN": clean(row.get("MPN")),
                "Footprint": clean(row.get("Footprint")),
                "Model3D": model,
                "ResolvedPath": str(resolved or ""),
                "Status": status,
            }
        )

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0].keys()))
        writer.writeheader()
        writer.writerows(output_rows)

    report = {
        "converted_parts": len(output_rows),
        "valid_model_3d": len(output_rows) - len(missing) - len(invalid),
        "missing": missing,
        "invalid": invalid,
    }
    args.output_report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"3D models: {report['valid_model_3d']}/{report['converted_parts']} valid; "
        f"missing={len(missing)}, invalid={len(invalid)}."
    )
    return 1 if missing or invalid else 0


if __name__ == "__main__":
    raise SystemExit(main())
