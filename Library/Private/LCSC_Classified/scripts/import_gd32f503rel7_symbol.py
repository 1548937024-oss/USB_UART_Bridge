#!/usr/bin/env python3
"""Import the verified GD32F503REL7 BGA64 symbol into the classified library."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

from library_metadata import extract_top_level_blocks, set_property, symbol_name


SYMBOL = "GD32F503REL7"
FOOTPRINT = "ucBGA-64_4x4mm_Layout8x8_P0.4mm"
MANUAL_KEY = "MANUAL-GD32F503REL7"
LOCAL_DATASHEET = (
    "../datasheets/MANUAL-GD32F503REL7/"
    "GD32F503xx_Datasheet_Rev0.9RC6.pdf"
)


def property_position(block: str, name: str, x: float, y: float) -> str:
    pattern = re.compile(
        rf'(\(property\s+"{re.escape(name)}"\s+"(?:[^"\\]|\\.)*"\s*'
        rf"\(at\s+)(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)(\))",
        flags=re.MULTILINE,
    )
    updated, count = pattern.subn(
        rf"\g<1>{x:g} {y:g} 0\g<5>",
        block,
        count=1,
    )
    if count != 1:
        raise ValueError(f"Property {name!r} position was not found")
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-library", type=Path, required=True)
    parser.add_argument("--library-root", type=Path, required=True)
    parser.add_argument("--kicad-root", type=Path, default=Path(r"D:\KiCad10.0"))
    args = parser.parse_args()

    source_text = args.source_library.resolve().read_text(encoding="utf-8")
    source_symbol = next(
        (
            block
            for block in extract_top_level_blocks(source_text, "symbol")
            if symbol_name(block) == SYMBOL
        ),
        None,
    )
    if source_symbol is None:
        raise ValueError(f"{SYMBOL} was not found in {args.source_library}")

    block = source_symbol
    values = {
        "Footprint": f"Embedded Processors & Controllers:{FOOTPRINT}",
        "Datasheet": "",
        "DatasheetRev": "Rev0.9RC6",
        "DatasheetDate": "",
        "LocalDatasheet": LOCAL_DATASHEET,
        "Manufacturer": "GigaDevice",
        "MPN": SYMBOL,
        "LCSC Part": MANUAL_KEY,
        "ki_keywords": "MCU Cortex-M33 GD32F503 BGA64 CAN-FD",
        "ki_description": (
            "GD32F503REL7 Cortex-M33 MCU, 512KB Flash, BGA-64 4x4mm"
        ),
        "Description": (
            "GD32F503REL7 Cortex-M33 MCU, 512KB Flash, BGA-64 4x4mm"
        ),
    }
    for name, value in values.items():
        block = set_property(block, name, value)
    block = property_position(block, "Reference", -7.62, 35.56)
    block = property_position(block, "Value", 7.62, -35.56)

    category = args.library_root.resolve() / "Embedded Processors & Controllers"
    library_path = category / "Embedded Processors & Controllers.kicad_sym"
    library_text = library_path.read_text(encoding="utf-8").rstrip()
    for existing in extract_top_level_blocks(library_text, "symbol"):
        if symbol_name(existing) == SYMBOL:
            library_text = library_text.replace(existing, "", 1).rstrip()
    if library_text.endswith(")"):
        library_text = library_text[:-1].rstrip()
    library_path.write_text(
        f"{library_text}\n\n{block}\n)\n",
        encoding="utf-8",
    )

    source_footprint = (
        args.kicad_root
        / "share"
        / "kicad"
        / "footprints"
        / "Package_BGA.pretty"
        / f"{FOOTPRINT}.kicad_mod"
    )
    footprint_dir = category / "Embedded Processors & Controllers.pretty"
    footprint_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_footprint, footprint_dir / source_footprint.name)

    print(f"Imported {SYMBOL} with {FOOTPRINT}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
