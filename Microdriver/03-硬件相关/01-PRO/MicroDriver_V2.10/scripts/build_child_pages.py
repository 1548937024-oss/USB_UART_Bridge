#!/usr/bin/env python3
"""Create the MicroDriver V2.10 child sheets.

Each child sheet gets its hierarchical labels so that the TOP sheet port map
resolves and ERC reports meaningful results.  The POWER page is fully drawn by
``build_power_page.py``; the remaining pages are drawn module by module.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402
from ports import PORTS, SHEET_FILES  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "MicroDriver_V2.10"
ROOT_UUID = k.make_uuid("root", PROJECT_NAME)

STUB_PAGES = ("MCU", "ENCODER", "communication", "MOTOR")


def build_stub(name: str) -> Path:
    stem, _page = SHEET_FILES[name]
    libraries = k.Libraries()
    libraries.register("power", PROJECT_ROOT / "library" / f"{PROJECT_NAME}.kicad_sym")

    sheet = k.Sheet(
        path=PROJECT_ROOT / f"{stem}.kicad_sch",
        project=PROJECT_NAME,
        uuid_key=stem,
        libraries=libraries,
        root_uuid=ROOT_UUID,
        sheet_uuid=k.make_uuid("sheet", stem),
    )

    sheet.text(
        f"title:{name}",
        f"MicroDriver V2.10 - {name}\n（本页按 PRJ_MicroDriver_V2.10.pdf 重建中）",
        20.32,
        15.24,
        1.5,
    )

    entries = PORTS[name]
    for index, (net, direction) in enumerate(entries):
        y = 30.48 + index * 5.08
        sheet.hier_label(net, 20.32, y, shape=direction, rotation=180)
        sheet.text(f"port:{net}", net, 22.86, y, 1.27)

    sheet.write()
    return sheet.path


def main() -> int:
    for name in STUB_PAGES:
        print(f"wrote {build_stub(name)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
