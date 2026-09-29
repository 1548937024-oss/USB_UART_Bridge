#!/usr/bin/env python3
"""Create the MicroDriver V2.10 project container.

Renames the imported symbol library, writes the library tables and rewrites
``MicroDriver_V2.10.kicad_pro`` so that the project references the V2.10
sheets and the AD style A4 drawing sheet.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "MicroDriver_V2.10"
ROOT_UUID = k.make_uuid("root", PROJECT_NAME)

# Sheet name, file stem, page number
SHEETS = [
    ("POWER", "SCH_MicroDriver_V2.10_POWER", "2"),
    ("MCU", "SCH_MicroDriver_V2.10_MCU", "3"),
    ("ENCODER", "SCH_MicroDriver_V2.10_ENCODER", "4"),
    ("communication", "SCH_MicroDriver_V2.10_communication", "5"),
    ("MOTOR", "SCH_MicroDriver_V2.10_MOTOR", "6"),
]

LEGACY_LIBRARY = PROJECT_ROOT / "library" / "PowerSymbols.kicad_sym"
PROJECT_LIBRARY = PROJECT_ROOT / "library" / f"{PROJECT_NAME}.kicad_sym"


def sheet_uuid(stem: str) -> str:
    return k.make_uuid("sheet", stem)


def normalise_library() -> None:
    if LEGACY_LIBRARY.is_file() and not PROJECT_LIBRARY.is_file():
        LEGACY_LIBRARY.rename(PROJECT_LIBRARY)
    if not PROJECT_LIBRARY.is_file():
        raise SystemExit(f"symbol library missing: {PROJECT_LIBRARY}")


def write_library_tables() -> None:
    symbol_dir = "${KICAD10_SYMBOL_DIR}"
    sym_lib_table = [
        "sym_lib_table",
        ["version", "7"],
        [
            "lib",
            ["name", k.quote("power")],
            ["type", k.quote("KiCad")],
            ["uri", k.quote(f"${{KIPRJMOD}}/library/{PROJECT_NAME}.kicad_sym")],
            ["options", k.quote("")],
            ["descr", k.quote("MicroDriver V2.10 project power symbols")],
        ],
        [
            "lib",
            ["name", k.quote(PROJECT_NAME)],
            ["type", k.quote("KiCad")],
            ["uri", k.quote(f"${{KIPRJMOD}}/library/{PROJECT_NAME}.kicad_sym")],
            ["options", k.quote("")],
            ["descr", k.quote("MicroDriver V2.10 project symbols")],
        ],
        [
            "lib",
            ["name", k.quote("Device")],
            ["type", k.quote("KiCad")],
            ["uri", k.quote(f"{symbol_dir}/Device.kicad_sym")],
            ["options", k.quote("")],
            ["descr", k.quote("KiCad standard device symbols")],
        ],
        [
            "lib",
            ["name", k.quote("Connector")],
            ["type", k.quote("KiCad")],
            ["uri", k.quote(f"{symbol_dir}/Connector.kicad_sym")],
            ["options", k.quote("")],
            ["descr", k.quote("KiCad standard connector symbols")],
        ],
        [
            "lib",
            ["name", k.quote("Mechanical")],
            ["type", k.quote("KiCad")],
            ["uri", k.quote(f"{symbol_dir}/Mechanical.kicad_sym")],
            ["options", k.quote("")],
            ["descr", k.quote("KiCad standard mechanical symbols")],
        ],
    ]

    fp_lib_table = [
        "fp_lib_table",
        ["version", "7"],
        [
            "lib",
            ["name", k.quote(PROJECT_NAME)],
            ["type", k.quote("KiCad")],
            ["uri", k.quote(f"${{KIPRJMOD}}/library/{PROJECT_NAME}.pretty")],
            ["options", k.quote("")],
            ["descr", k.quote("MicroDriver V2.10 project footprints")],
        ],
        [
            "lib",
            ["name", k.quote("TestPoint")],
            ["type", k.quote("KiCad")],
            ["uri", k.quote("${KICAD10_FOOTPRINT_DIR}/TestPoint.pretty")],
            ["options", k.quote("")],
            ["descr", k.quote("KiCad standard test point footprints")],
        ],
    ]

    (PROJECT_ROOT / "sym-lib-table").write_text(
        k.serialize(sym_lib_table) + "\n", encoding="utf-8", newline="\n"
    )
    (PROJECT_ROOT / "fp-lib-table").write_text(
        k.serialize(fp_lib_table) + "\n", encoding="utf-8", newline="\n"
    )


def write_project_file() -> None:
    path = PROJECT_ROOT / f"{PROJECT_NAME}.kicad_pro"
    data = json.loads(path.read_text(encoding="utf-8"))

    data["meta"]["filename"] = path.name
    data["schematic"]["page_layout_descr_file"] = (
        "${KIPRJMOD}/AD_Style_A4.kicad_wks"
    )
    data["pcbnew"]["page_layout_descr_file"] = "${KIPRJMOD}/AD_Style_A4.kicad_wks"
    data["schematic"]["top_level_sheets"] = [
        {
            "filename": f"{PROJECT_NAME}.kicad_sch",
            "name": "TOP",
            "uuid": ROOT_UUID,
        }
    ]
    data["schematic"]["sheets"] = [
        [ROOT_UUID, "TOP"],
        *[[sheet_uuid(stem), name] for name, stem, _ in SHEETS],
    ]
    data["schematic"]["used_designators"] = ""

    variables = data["text_variables"]
    variables["@PROJECT NAME"] = "MicroDriver V2.10"
    variables["@SCHEMATIC NAME"] = "外置驱动器 MicroDriver V2.10"
    variables["@PAGE NAME"] = "外置驱动器"
    variables["@PAGE COUNT"] = str(len(SHEETS))
    variables["@CREATE DATE"] = "2026-05-29"
    variables["@UPDATE DATE"] = "2026-09-29"
    variables["VERSION"] = "V2.10"
    variables["SHEETTOTAL"] = str(len(SHEETS))
    variables["PAGE SIZE"] = "A4"
    variables["DRAWED"] = "李鹏"
    variables["DESIGNATOR"] = ""

    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    normalise_library()
    write_library_tables()
    write_project_file()
    print(f"project container ready in {PROJECT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
