#!/usr/bin/env python3
"""Normalize footprint 3D model paths and optionally remove broken references."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from library_metadata import extract_top_level_blocks


OLD_PREFIXES = (
    "D:/办公相关/项目相关/三花/03-灵巧手项目/O-外置驱动器/"
    "Library/Private/LCSC_Classified/libraries/",
    "D:\\办公相关\\项目相关\\三花\\03-灵巧手项目\\O-外置驱动器\\"
    "Library\\Private\\LCSC_Classified\\libraries\\",
)
MODEL_PATTERN = re.compile(r'\(model\s+"([^"]+)"')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--prune-missing", action="store_true")
    parser.add_argument("--kicad-root", type=Path, default=Path(r"D:\KiCad10.0"))
    return parser.parse_args()


def normalize_model_path(model: str) -> tuple[str, bool]:
    for prefix in OLD_PREFIXES:
        if model.startswith(prefix):
            return "${LCSC_LIB_ROOT}/" + model[len(prefix) :].replace("\\", "/"), True
    return model.replace("\\", "/"), False


def resolve_model_path(model: str, library_root: Path, kicad_root: Path) -> Path | None:
    if model.startswith("${LCSC_LIB_ROOT}/"):
        relative = model[len("${LCSC_LIB_ROOT}/") :]
        return (library_root / relative).resolve()
    if model.startswith("${KICAD10_3DMODEL_DIR}/"):
        relative = model[len("${KICAD10_3DMODEL_DIR}/") :]
        return (kicad_root / "share" / "kicad" / "3dmodels" / relative).resolve()
    return None


def main() -> int:
    args = parse_args()
    library_root = args.library_root.resolve()
    kicad_root = args.kicad_root.resolve()
    report_rows: list[dict[str, str]] = []
    changed_files = 0
    normalized_count = 0
    valid_count = 0
    missing_count = 0
    pruned_count = 0

    for footprint in sorted(library_root.rglob("*.kicad_mod")):
        original = footprint.read_text(encoding="utf-8")
        text = original
        for block in extract_top_level_blocks(text, "model"):
            match = MODEL_PATTERN.search(block)
            if not match:
                continue
            model = match.group(1)
            normalized, changed = normalize_model_path(model)
            resolved = resolve_model_path(normalized, library_root, kicad_root)
            exists = bool(resolved and resolved.is_file())
            action = "KEEP"
            if changed:
                text = text.replace(block, block.replace(model, normalized, 1), 1)
                normalized_count += 1
            if exists:
                valid_count += 1
            elif resolved is None:
                valid_count += 1
                action = "UNVERIFIED"
            elif args.prune_missing:
                text = text.replace(block, "", 1)
                pruned_count += 1
                action = "PRUNED"
            else:
                missing_count += 1
                action = "MISSING"
            report_rows.append(
                {
                    "Footprint": footprint.stem,
                    "Model": normalized,
                    "Action": action,
                    "ResolvedPath": str(resolved or ""),
                }
            )
        text = re.sub(r"\n{3,}", "\n\n", text)
        if text != original:
            footprint.write_text(text, encoding="utf-8")
            changed_files += 1

    report = {
        "footprint_files_changed": changed_files,
        "models_normalized": normalized_count,
        "models_valid": valid_count,
        "models_missing": missing_count,
        "models_pruned": pruned_count,
        "entries": report_rows,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"3D paths: normalized={normalized_count}, valid={valid_count}, "
        f"missing={missing_count}, pruned={pruned_count}, files={changed_files}."
    )
    return 1 if missing_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
