#!/usr/bin/env python3
"""Create the LA150C RDIVER V1.00 project container.

Writes the library tables and the ``.kicad_pro`` so that the project
references the regenerated sheets and the AD style A4 drawing sheet.  The
container is rebuilt from the imported Altium project file so the ERC
severity settings and net classes survive.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402
from ports import SHEET_FILES  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "LA150C_RDIVER_V1.00"
ROOT_UUID = k.make_uuid("root", PROJECT_NAME)

LEGACY_PRO = PROJECT_ROOT / "PRO_LA150C_RDIVER_V1.00.kicad_pro"
PROJECT_FILE = PROJECT_ROOT / f"{PROJECT_NAME}.kicad_pro"
PROJECT_LIBRARY = PROJECT_ROOT / "library" / f"{PROJECT_NAME}.kicad_sym"


def sheet_uuid(stem: str) -> str:
    return k.make_uuid("sheet", stem)


def write_library_tables() -> None:
    symbol_dir = "${KICAD10_SYMBOL_DIR}"
    sym_lib_table = [
        "sym_lib_table",
        ["version", "7"],
        [
            "lib",
            ["name", k.quote(PROJECT_NAME)],
            ["type", k.quote("KiCad")],
            ["uri", k.quote(f"${{KIPRJMOD}}/library/{PROJECT_NAME}.kicad_sym")],
            ["options", k.quote("")],
            ["descr", k.quote("LA150C RDIVER V1.00 project symbols")],
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
            ["name", k.quote("Transistor_FET")],
            ["type", k.quote("KiCad")],
            ["uri", k.quote(f"{symbol_dir}/Transistor_FET.kicad_sym")],
            ["options", k.quote("")],
            ["descr", k.quote("KiCad standard FET symbols")],
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
            ["descr", k.quote("LA150C RDIVER V1.00 project footprints")],
        ],
        [
            "lib",
            ["name", k.quote("TestPoint")],
            ["type", k.quote("KiCad")],
            ["uri", k.quote("${KICAD10_FOOTPRINT_DIR}/TestPoint.pretty")],
            ["options", k.quote("")],
            ["descr", k.quote("KiCad standard test point footprints")],
        ],
        [
            "lib",
            ["name", k.quote("Connector_PinHeader_1.00mm")],
            ["type", k.quote("KiCad")],
            ["uri", k.quote("${KICAD10_FOOTPRINT_DIR}/Connector_PinHeader_1.00mm.pretty")],
            ["options", k.quote("")],
            ["descr", k.quote("KiCad standard 1.00mm pin header footprints")],
        ],
    ]

    # Footprints that come with the classified LCSC libraries.  The path is
    # relative to the project so the container stays portable inside the repo.
    classified = (
        "${KIPRJMOD}/../../../../Library/Private/LCSC_Classified/libraries"
    )
    for category in (
        "Capacitors",
        "Circuit Protection",
        "Connectors",
        "Crystals, Oscillators, Resonators",
        "Diodes",
        "Embedded Processors & Controllers",
        "Filters",
        "Inductors, Coils, Chokes",
        "Industrial control electrical",
        "Interface",
        "Magnetic Sensors",
        "Memory",
        "Motor Driver ICs",
        "Optoelectronics",
        "Power Management (PMIC)",
        "Resistors",
        "Sensors",
        "Switches",
        "Transistors",
    ):
        fp_lib_table.append(
            [
                "lib",
                ["name", k.quote(category)],
                ["type", k.quote("KiCad")],
                ["uri", k.quote(f"{classified}/{category}/{category}.pretty")],
                ["options", k.quote("")],
                ["descr", k.quote(f"LCSC classified {category} footprints")],
            ]
        )

    (PROJECT_ROOT / "sym-lib-table").write_text(
        k.serialize(sym_lib_table) + "\n", encoding="utf-8", newline="\n"
    )
    (PROJECT_ROOT / "fp-lib-table").write_text(
        k.serialize(fp_lib_table) + "\n", encoding="utf-8", newline="\n"
    )


def write_project_file() -> None:
    if LEGACY_PRO.is_file():
        data = json.loads(LEGACY_PRO.read_text(encoding="utf-8"))
    elif PROJECT_FILE.is_file():
        data = json.loads(PROJECT_FILE.read_text(encoding="utf-8"))
    else:
        raise SystemExit(f"neither {LEGACY_PRO.name} nor {PROJECT_FILE.name} exists")

    data["meta"]["filename"] = PROJECT_FILE.name
    data["schematic"]["page_layout_descr_file"] = "${KIPRJMOD}/AD_Style_A4.kicad_wks"
    data["pcbnew"]["page_layout_descr_file"] = "${KIPRJMOD}/AD_Style_A4.kicad_wks"
    data["schematic"]["top_level_sheets"] = [
        {"filename": f"{PROJECT_NAME}.kicad_sch", "name": PROJECT_NAME, "uuid": ROOT_UUID}
    ]
    data["sheets"] = [
        [ROOT_UUID, PROJECT_NAME],
        *[[sheet_uuid(stem), name] for name, (stem, _page) in SHEET_FILES.items()],
    ]
    data["schematic"]["used_designators"] = ""

    variables = data["text_variables"]
    variables["@PROJECT NAME"] = "LA150C RDIVER V1.00"
    variables["@SCHEMATIC NAME"] = "LA150C 集成驱动器"
    variables["@PAGE NAME"] = "集成驱动器"
    variables["@PAGE NO"] = "1"
    variables["@PAGE COUNT"] = str(len(SHEET_FILES) + 1)
    variables["@CREATE DATE"] = "2026-09-22"
    variables["@UPDATE DATE"] = "2026-10-11"
    variables["VERSION"] = "V1.00"
    variables["SHEETTOTAL"] = str(len(SHEET_FILES) + 1)
    variables["PAGE SIZE"] = "A4"
    variables["DRAWED"] = "李鹏"
    variables["DESIGNATOR"] = ""

    PROJECT_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def archive_legacy_sheets() -> None:
    """Move the pre-generator Altium-derived sheets out of the working set."""
    archive = PROJECT_ROOT / "_legacy_altium"
    archive.mkdir(exist_ok=True)
    for name in ("PRO_LA150C_RDIVER_V1.00.kicad_sch",):
        source = PROJECT_ROOT / name
        if source.is_file():
            shutil.move(str(source), str(archive / name))


def main() -> int:
    if not PROJECT_LIBRARY.is_file():
        raise SystemExit(f"symbol library missing: {PROJECT_LIBRARY}")
    write_library_tables()
    write_project_file()
    archive_legacy_sheets()
    print(f"project container ready: {PROJECT_FILE.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
