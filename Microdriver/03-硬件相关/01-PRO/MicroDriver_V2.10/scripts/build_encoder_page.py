#!/usr/bin/env python3
"""Build the MicroDriver V2.10 ENCODER sheet.

Layout follows PRJ_MicroDriver_V2.10.pdf page 3: the nine channels are grouped
(ABZ 3, BiSS-C 2, SPI 4).  Each channel runs left to right through a series
100 R, a test point and on to the MCU-side port.  The ESD diode and the
100 pF capacitor tap the *connector* side of the series resistor, are drawn as
two horizontal rows below the signal rows, and return to a shared GND rail.

Only the electrically symmetric two-terminal parts are rotated, so the drawing
never depends on KiCad's rotation convention.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "MicroDriver_V2.10"
ROOT_UUID = k.make_uuid("root", PROJECT_NAME)
STEM = "SCH_MicroDriver_V2.10_ENCODER"

GROUPS = [
    ("ENCODER ABZ", 33.02, [
        ("EC-A", "ENCODER-A", "R23", "D9", "C35"),
        ("EC-B", "ENCODER-B", "R24", "D10", "C36"),
        ("EC-Z", "ENCODER-Z", "R25", "D11", "C37"),
    ]),
    ("BISS-C", 86.36, [
        ("CLK", "MA", "R26", "D12", "C38"),
        ("DATA", "SLO", "R27", "D13", "C39"),
    ]),
    ("SPI", 124.46, [
        ("NSS", "SPI-NSS", "R28", "D14", "C40"),
        ("SCK", "SPI-SCK", "R29", "D15", "C41"),
        ("MOSI", "SPI-MOSI", "R30", "D16", "C42"),
        ("MISO", "SPI-MISO", "R31", "D17", "C43"),
    ]),
]

ROW_PITCH = 15.24          # one signal row per channel; ESD/cap hang below
LABEL_X = 25.4             # input (connector side) label, rotated 180 deg
ESD_X0 = 55.88             # ESD taps the connector side, before the series R
ESD_PITCH = 7.62
R_X = 96.52                # series 100R, pins at 92.71 / 100.33
CAP_X0 = 116.84            # RC filter taps after the series R
CAP_PITCH = 7.62
TP_X = 149.86
PORT_X = 167.64            # MCU-side label
GND_DROP = 15.24           # rail offset below the last signal row

PWR_X = 213.36


def main() -> int:
    project_library = PROJECT_ROOT / "library" / f"{PROJECT_NAME}.kicad_sym"
    libraries = k.Libraries()
    libraries.register("power", project_library)
    libraries.register(PROJECT_NAME, project_library)
    libraries.register("Device", Path(r"D:\KiCad10.0\share\kicad\symbols\Device.kicad_sym"))

    sheet = k.Sheet(
        path=PROJECT_ROOT / f"{STEM}.kicad_sch",
        project=PROJECT_NAME,
        uuid_key=STEM,
        libraries=libraries,
        root_uuid=ROOT_UUID,
        sheet_uuid=k.make_uuid("sheet", STEM),
        power_base=200,
        flag_base=100,
        power_rotation=180,
    )

    sheet.text(
        "title",
        "MicroDriver V2.10 - ENCODER\n编码器接口 ABZ / BiSS-C / SPI：每路 100R 串阻 + ESD + 100pF"
        "，取样点在串阻之前的编码器侧",
        20.32,
        17.78,
        1.5,
    )
    sheet.text("note:place", "旁路电容和 ESD 管靠近编码器接口放置", 20.32, 25.4)

    pwr_ref = 200
    tp_ref = 0
    gnd_flag_done = False
    for group_name, gy, channels in GROUPS:
        n = len(channels)
        rail_y = gy + (n - 1) * ROW_PITCH + GND_DROP
        esd_xs = [ESD_X0 + i * ESD_PITCH for i in range(n)]
        cap_xs = [CAP_X0 + i * CAP_PITCH for i in range(n)]

        sheet.block(group_name, 19.05, gy - 6.35, 179.07, rail_y + 5.08)
        sheet.text(f"gname:{group_name}", group_name, 27.94, gy - 1.27, 1.5)

        for index, (left_net, right_net, r_ref, d_ref, c_ref) in enumerate(channels):
            y = gy + index * ROW_PITCH
            esd_x = esd_xs[index]
            cap_x = cap_xs[index]

            # connector side -> series resistor -> test point -> MCU side
            sheet.hier_label(left_net, LABEL_X, y, shape="input", rotation=180)
            sheet.component("Device:R", r_ref, "100R", R_X, y, rotation=90,
                            footprint="", description="0201 100R 1%")
            sheet.wire(LABEL_X, y, R_X - 3.81, y)
            sheet.wire(R_X + 3.81, y, PORT_X, y)
            tp_ref += 1
            sheet.component(f"{PROJECT_NAME}:TP0.8", f"TP{tp_ref:02d}", "TP",
                            TP_X, y, footprint="", description="测试点")
            sheet.junction(TP_X, y)
            sheet.hier_label(right_net, PORT_X, y, shape="output", rotation=0)

            # ESD: vertical, hanging straight down from the connector side
            sheet.junction(esd_x, y)
            sheet.wire(esd_x, y, esd_x, y + 2.54)
            sheet.component(f"{PROJECT_NAME}:PESDNC2XD5VB", d_ref, "PESDNC2XD5VB",
                            esd_x, y + 7.62, rotation=90, footprint="",
                            description="DFN0603-2L 5V ESD")
            sheet.wire(esd_x, y + 12.7, esd_x, rail_y)
            sheet.junction(esd_x, rail_y)

            # RC filter: vertical, hanging straight down after the series resistor
            sheet.junction(cap_x, y)
            sheet.wire(cap_x, y, cap_x, y + 2.54)
            sheet.component("Device:C", c_ref, "100pF", cap_x, y + 6.35, rotation=0,
                            footprint="", description="0201 100pF 50V")
            sheet.wire(cap_x, y + 10.16, cap_x, rail_y)
            sheet.junction(cap_x, rail_y)

        # shared GND rail for the group
        rail_left = esd_xs[0]
        rail_right = cap_xs[-1]
        sheet.wire(rail_left, rail_y, rail_right, rail_y)
        pwr_ref += 1
        sheet.power("power:GND_POWER_GROUND", f"#PWR{pwr_ref:02d}", rail_left, rail_y)
        # No PWR_FLAG here: the GND net is declared once on the POWER sheet.

    # encoder supply selection, placed clear of the channel field
    base_x = PWR_X
    vy = 45.72
    sheet.block("ENCODER SUPPLY", base_x - 7.62, vy - 15.24, base_x + 53.34, vy + 20.32)
    sheet.power("power:+3.3V_BAR", "#PWR90", base_x, vy)
    sheet.wire(base_x, vy, base_x + 5.08, vy)
    sheet.component("Device:R", "R44", "0R", base_x + 8.89, vy, rotation=90,
                    footprint="", description="0402 0R, NC = 5V 不供")
    sheet.wire(base_x + 12.7, vy, base_x + 33.02, vy)
    sheet.power("power:+5V_BAR", "#PWR91", base_x + 43.18, vy)
    sheet.wire(base_x + 33.02, vy, base_x + 43.18, vy)
    sheet.junction(base_x + 33.02, vy)
    sheet.component("Device:C", "C34", "100nF", base_x + 33.02, vy + 3.81,
                    footprint="", description="0201 100nF 16V")
    sheet.wire(base_x + 33.02, vy + 7.62, base_x + 33.02, vy + 12.7)
    sheet.power("power:GND_POWER_GROUND", "#PWR92", base_x + 33.02, vy + 12.7)
    sheet.text("note:r44", "R44: 0R(default)=3.3V；NC=不供 5V", base_x - 5.08, vy - 10.16)

    sheet.write()
    print(f"wrote {sheet.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
