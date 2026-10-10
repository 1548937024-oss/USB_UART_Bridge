#!/usr/bin/env python3
"""Build the LA150C ENCODER sheet (MT6701QT-STD, SSI mode).

The symbol and footprint come from the classified LCSC library and match
QS01 EBOM U5.  MT6701 pin 9 is W, pin 11 is U and pin 12 is V; this differs
from the earlier local symbol and is the main pin-mapping correction here.
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
        "LA150C RDIVER V1.00 - ENCODER\n"
        "MT6701QT-STD 磁编码器 SSI：14bit 角度 + 4bit 磁场状态 + 6bit CRC，CLK 8MHz",
        20.32,
        15.24,
        1.5,
    )
    sheet.block("E  磁编码器 MT6701QT-STD (SSI)", 22.86, 24.13, 261.62, 132.08)

    u = f"{P}:MT6701QT-STD_C2913974"
    ux, uy = 142.24, 100.33
    sheet.component(
        u,
        "U2",
        "MT6701QT-STD",
        ux,
        uy,
        footprint="",
        description="MT6701QT-STD 14-bit magnetic angle sensor, QFN-16",
    )

    def up(n: str) -> tuple[float, float]:
        return sheet.pin(u, ux, uy, 0, n)

    # SSI signal pins: A/DO = 6, B/CLK = 7, Z/CSN = 8.
    a, b, z = up("6"), up("7"), up("8")
    for net, point, shape in (
        ("SPI2_MISO", a, "output"),
        ("SPI2_SCK", b, "input"),
        ("SPI2_CSN", z, "input"),
    ):
        sheet.wire(point[0], point[1], 66.04, point[1])
        sheet.hier_label(net, 66.04, point[1], shape=shape, rotation=180)

    # VDD rail, MODE strap and local decoupling.
    vdd, mode = up("13"), up("14")
    rail_y = 96.52
    sheet.component("Device:C", "C11", "100nF", 177.8, 100.33, footprint="",
                    description="0201 100nF 16V VDD 去耦")
    sheet.component("Device:C", "C12", "1uF", 185.42, 100.33, footprint="",
                    description="0402 1uF 10V VDD 去耦")
    c11_a = sheet.pin("Device:C", 177.8, 100.33, 0, "1")
    c11_b = sheet.pin("Device:C", 177.8, 100.33, 0, "2")
    c12_a = sheet.pin("Device:C", 185.42, 100.33, 0, "1")
    c12_b = sheet.pin("Device:C", 185.42, 100.33, 0, "2")

    # VDD pin -> rail -> power symbol.
    sheet.wire(vdd[0], vdd[1], 172.72, vdd[1])
    sheet.wire(172.72, vdd[1], 172.72, rail_y)
    sheet.power(f"{P}:PWR_3V3", "#PWR201", 165.1, 92.71)
    sheet.wire(165.1, 92.71, 165.1, rail_y)
    sheet.junction(172.72, rail_y)

    # MODE pin -> rail.
    sheet.wire(mode[0], mode[1], 166.37, mode[1])
    sheet.wire(166.37, mode[1], 166.37, rail_y)
    sheet.junction(166.37, rail_y)
    sheet.wire(165.1, rail_y, 185.42, rail_y)

    # Decoupling caps sit directly on the rail; return to one local GND.
    for top, bottom in ((c11_a, c11_b), (c12_a, c12_b)):
        sheet.junction(top[0], rail_y)
        sheet.wire(bottom[0], bottom[1], bottom[0], 107.95)
    sheet.wire(c11_b[0], 107.95, c12_b[0], 107.95)
    sheet.power(f"{P}:GND", "#PWR202", c11_b[0], 107.95)
    sheet.junction(c11_b[0], 107.95)
    sheet.text(
        "note:mode",
        "★ MODE(14) 接 PWR_3V3 = SSI；误接地会静默切到 ABZ。VDD(13) 就近 100nF + 1µF。",
        194.31,
        94.0,
        1.27,
    )

    # GND(16) and EP(17) return separately to avoid crossing the VDD rail.
    gnd_pin, ep = up("16"), up("17")
    sheet.wire(gnd_pin[0], gnd_pin[1], 160.02, gnd_pin[1])
    sheet.wire(160.02, gnd_pin[1], 160.02, 111.76)
    sheet.power(f"{P}:GND", "#PWR203", 160.02, 111.76)
    sheet.wire(ep[0], ep[1], 195.58, ep[1])
    sheet.wire(195.58, ep[1], 195.58, 111.76)
    sheet.power(f"{P}:GND", "#PWR204", 195.58, 111.76)

    # Unused pins in SSI mode.
    for point in (
        up("1"), up("2"), up("3"), up("4"), up("5"),
        up("9"), up("10"), up("11"), up("12"), up("15"),
    ):
        sheet.no_connect(point[0], point[1])

    sheet.text(
        "note:ssi",
        "SSI：CSN 拉低 → 24 个 CLK → 14bit 角度 + 4bit 磁场状态 + 6bit CRC"
        "（X⁶+X+1, MSB first）；CLK 上升沿更新 DO。",
        26.67,
        118.11,
        1.27,
    )
    sheet.text(
        "note:pins",
        "MT6701QT-STD 引脚校正：9=W、11=U、12=V；SSI 模式仅使用 6/7/8/13/14/16/17。",
        26.67,
        123.19,
        1.27,
    )
    sheet.text(
        "note:asm",
        "磁体 Ø6×2.5mm N35SH 径向两极，气隙 0.5~2.0mm（典型 1.0mm），偏心 ≤0.3mm（结构件，不上图）",
        26.67,
        128.27,
        1.27,
    )

    sheet.write()
    print(f"wrote {sheet.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
