#!/usr/bin/env python3
"""Clone the verified MT6701 ACD symbol for the EBOM STD variant."""

from __future__ import annotations

import argparse
from pathlib import Path

from library_metadata import (
    extract_top_level_blocks,
    property_value,
    set_property,
    symbol_name,
)


SOURCE_LCSC = "C49257133"
TARGET_LCSC = "C2913974"
TARGET_NAME = "MT6701QT-STD_C2913974"
TARGET_MPN = "MT6701QT-STD"
TARGET_FOOTPRINT = "Magnetic Sensors:VQFN-16_L3.0-W3.0-P0.50-TL-EP1.7"
TARGET_DATASHEET = (
    "https://atta.szlcsc.com/upload/public/pdf/source/20260616/"
    "FEB700C1922508565884FF0A90656B50.pdf"
)
TARGET_LOCAL_DATASHEET = "../datasheets/C2913974/MT6701QT-STD.pdf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    library_path = (
        args.library_root.resolve()
        / "Magnetic Sensors"
        / "Magnetic Sensors.kicad_sym"
    )
    text = library_path.read_text(encoding="utf-8")
    source = next(
        (
            block
            for block in extract_top_level_blocks(text, "symbol")
            if property_value(block, "LCSC Part").strip().upper()
            == SOURCE_LCSC
        ),
        None,
    )
    if source is None:
        raise ValueError(f"{SOURCE_LCSC} symbol was not found")

    old_name = symbol_name(source)
    clone = source.replace(f'"{old_name}"', f'"{TARGET_NAME}"')
    clone = clone.replace(f'"{old_name}_', f'"{TARGET_NAME}_')
    properties = {
        "Value": TARGET_NAME,
        "Footprint": TARGET_FOOTPRINT,
        "Datasheet": TARGET_DATASHEET,
        "DatasheetRev": "Rev1.5",
        "DatasheetDate": "2021-03",
        "LocalDatasheet": TARGET_LOCAL_DATASHEET,
        "Manufacturer": "NOVOSENSE(纳芯微)",
        "MPN": TARGET_MPN,
        "LCSC Part": TARGET_LCSC,
        "Description": "MT6701 QFN-16 magnetic angle sensor, standard variant",
        "ki_description": "MT6701 QFN-16 magnetic angle sensor, standard variant",
    }
    for name, value in properties.items():
        clone = set_property(clone, name, value)

    for existing in extract_top_level_blocks(text, "symbol"):
        if symbol_name(existing) == TARGET_NAME:
            text = text.replace(existing, "", 1).rstrip()
    text = text.rstrip()
    if not text.endswith(")"):
        raise ValueError("Magnetic Sensors symbol library became invalid")
    library_path.write_text(
        text[:-1].rstrip() + "\n\n" + clone + "\n)\n",
        encoding="utf-8",
    )
    print(f"Added {TARGET_NAME} from {SOURCE_LCSC}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
