#!/usr/bin/env python3
"""Build the LA150C ENCODER sheet (MT6701, SSI mode).

Hardware design doc §3.7: SSI frame = 14-bit angle + 4-bit field status +
6-bit CRC, CLK 8 MHz, DO driven on the rising edge.  MODE must be tied high
to VDD; tying it low silently selects ABZ, so the schematic calls it out.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "LA150C_RDIVER_V1.00"
ROOT_UUID = k.make_uuid("root", PROJECT_NAME)
STEM = "SCH_LA150C_ENCODER_V1.00"
P = PROJECT_NAME


def main() -> int:
    lib = PROJECT_ROOT / "library" / f"{PROJECT_NAME}.kicad_sym"
    libraries = k.Libraries()
    libraries.register(PROJECT_NAME, lib)
    libraries.register("Device", Path(r"D:\KiCad10.0\share\kicad\symbols\Device.kicad_sym"))

    sheet = k.Sheet(
        path=PROJECT_ROOT / f"{STEM}.kicad_sch",
        project=PROJECT_NAME,
        uuid_key=STEM,
        libraries=libraries,
        root_uuid=ROOT_UUID,
        sheet_uuid=k.make_uuid("sheet", STEM),
        power_base=200,
        flag_base=200,
        power_rotation=0,
    )
    sheet.text(
        "title",
        "LA150C RDIVER V1.00 - ENCODER\nMT6701 磁编码器 SSI：14bit 角度 + 4bit 磁场状态 + 6bit CRC，CLK 8MHz",
        20.32,
        15.24,
        1.5,
    )
    sheet.block("E  磁编码器 MT6701 (SSI)", 22.86, 24.13, 231.14, 132.08)

    u = f"{P}:MT6701"
    ux, uy = 107.95, 90.17
    sheet.component(u, "U2", "MT6701", ux, uy, footprint="", description="QFN-16 磁编码器")

    def up(n):
        return sheet.pin(u, ux, uy, 0, n)

    push, a, b, z = up("5"), up("6"), up("7"), up("8")
    nc1, nc2, nc3, nc4 = up("1"), up("2"), up("3"), up("4")
    vdd, mode, out, uu, nc5, vv, ww, gnd = (
        up("13"), up("14"), up("15"), up("9"), up("10"), up("11"), up("12"), up("16"),
    )
    ep = up("17")

    # signal ports towards the MCU
    sheet.wire(a[0], a[1], 66.04, a[1])
    sheet.hier_label("SPI2_MISO", 66.04, a[1], shape="output", rotation=180)
    sheet.text("note:a", "A/DO: SSI 数据输出，CLK 上升沿驱动", 26.67, 30.48, 1.27)
    sheet.wire(b[0], b[1], 66.04, b[1])
    sheet.hier_label("SPI2_SCK", 66.04, b[1], shape="input", rotation=180)
    sheet.wire(z[0], z[1], 66.04, z[1])
    sheet.hier_label("SPI2_CSN", 66.04, z[1], shape="input", rotation=180)

    # power and MODE
    rail_y = vdd[1]
    sheet.wire(vdd[0], vdd[1], 139.7, rail_y)
    sheet.power(f"{P}:PWR_3V3", "#PWR201", 139.7, 76.2)
    sheet.wire(139.7, 76.2, 139.7, rail_y)

    for refc, val, desc, x in (
        ("C11", "100nF", "0402 100nF 16V", 127.0),
        ("C12", "1uF", "0402 1uF 10V", 134.62),
    ):
        sheet.component("Device:C", refc, val, x, 88.9, footprint="", description=desc)
        top = sheet.pin("Device:C", x, 88.9, 0, "1")
        bot = sheet.pin("Device:C", x, 88.9, 0, "2")
        sheet.wire(x, rail_y, top[0], top[1])
        sheet.junction(x, rail_y)
        sheet.wire(bot[0], bot[1], bot[0], 97.79)
    sheet.wire(127.0, 97.79, 134.62, 97.79)
    sheet.power(f"{P}:GND", "#PWR202", 127.0, 97.79)
    sheet.junction(127.0, 97.79)

    # MODE tied to VDD -> SSI (must be annotated)
    sheet.wire(mode[0], mode[1], 124.46, mode[1])
    sheet.wire(124.46, mode[1], 124.46, rail_y)
    sheet.junction(124.46, rail_y)
    sheet.text(
        "note:mode",
        "★ MODE 接 PWR_3V3 = SSI 模式；误接地会静默切到 ABZ，读到全 0 或跳变数据",
        140.97,
        mode[1] - 1.27,
        1.27,
    )

    # ground
    sheet.wire(gnd[0], gnd[1], 137.16, gnd[1])
    sheet.wire(137.16, gnd[1], 137.16, 104.14)
    sheet.power(f"{P}:GND", "#PWR203", 137.16, 104.14)
    sheet.wire(ep[0], ep[1], ep[0], 109.22)
    sheet.power(f"{P}:GND", "#PWR204", ep[0], 109.22)

    # unused pins
    for name, point in (
        ("PUSH", push), ("OUT", out), ("U", uu), ("V", vv), ("W", ww),
        ("NC1", nc1), ("NC2", nc2), ("NC3", nc3), ("NC4", nc4), ("NC5", nc5),
    ):
        sheet.no_connect(point[0], point[1])

    sheet.text(
        "note:ssi",
        "SSI：CSN 拉低 → 24 个 CLK → 14bit 角度 + 4bit 磁场状态 + 6bit CRC(X⁶+X+1, MSB first)。"
        " 帧长 3µs + 5µs 传播延迟 → 125kHz 更新率，远高于 FOC 电流环需求。",
        26.67,
        118.11,
        1.27,
    )
    sheet.text(
        "note:asm",
        "磁体 Ø6×2.5mm N35SH 径向两极，气隙 0.5~2.0mm（典型 1.0mm），偏心 ≤0.3mm（结构件，不上图）",
        26.67,
        123.19,
        1.27,
    )
    sheet.text(
        "note:var",
        "VDD 去耦 100nF + 1µF；U/V/W 与 PUSH/OUT/NC 在 SSI 模式下不用，全部置 no_connect",
        26.67,
        128.27,
        1.27,
    )
    sheet.write()
    print(f"wrote {sheet.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
