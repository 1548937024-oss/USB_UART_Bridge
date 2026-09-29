#!/usr/bin/env python3
"""Build the MicroDriver V2.10 TOP (root) sheet."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402
from ports import PORTS, SHEET_FILES, SHEET_PLACEMENT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "MicroDriver_V2.10"

PIN_PITCH = 2.54
PIN_TOP_OFFSET = 7.62


def main() -> int:
    libraries = k.Libraries()
    libraries.register("power", PROJECT_ROOT / "library" / f"{PROJECT_NAME}.kicad_sym")

    root_uuid = k.make_uuid("root", PROJECT_NAME)
    sheet = k.Sheet(
        path=PROJECT_ROOT / f"{PROJECT_NAME}.kicad_sch",
        project=PROJECT_NAME,
        uuid_key="root",
        libraries=libraries,
        root_uuid=root_uuid,
        page="1",
    )

    for name, (stem, page) in SHEET_FILES.items():
        x, y, width, height = SHEET_PLACEMENT[name]
        entries = PORTS[name]
        left = [item for item in entries if item[1] == "input"]
        right = [item for item in entries if item[1] != "input"]
        required = max(len(left), len(right)) * PIN_PITCH + PIN_TOP_OFFSET + 2.54
        if required > height:
            raise ValueError(
                f"{name}: sheet height {height} is too small for {required:.2f} mm of pins"
            )

        pins: list[tuple[str, str, float, float, float]] = []
        for index, (net, direction) in enumerate(left):
            pins.append((net, direction, x, y + PIN_TOP_OFFSET + index * PIN_PITCH, 180))
        for index, (net, direction) in enumerate(right):
            pins.append(
                (net, direction, x + width, y + PIN_TOP_OFFSET + index * PIN_PITCH, 0)
            )

        sheet.subsheet(
            name=name,
            filename=f"{stem}.kicad_sch",
            x=x,
            y=y,
            width=width,
            height=height,
            uuid=k.make_uuid("sheet", stem),
            page=page,
            pins=pins,
        )

    sheet.text(
        "title",
        "MicroDriver V2.10 - TOP\n层次页：电源 / MCU / 编码器 / 通信 / 电机驱动",
        25.4,
        17.78,
        1.5,
    )
    sheet.text(
        "note:power",
        "电源网络（VBUS_IN / VBUS / 5V / 3.3V / GND / EGND）为全局电源符号，不在本页连线。\n"
        "本页为 V2.10 重建骨架：连接器 J1-J10 待补。",
        25.4,
        177.8,
    )

    sheet.write()
    print(f"wrote {sheet.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
