#!/usr/bin/env python3
"""Build the LA150C MCU sheet (GD32F503REL7, BGA-64).

QS01/QSO3 baseline: BGA-64 ball numbering, external-driver-compatible
8 MHz resonator, SWD on PA13/PA14/NRST, VDD bank + VDDA/VREFP decoupling,
BOOT0 / BOOT1 pulled low.  Every unused pin gets an explicit no-connect.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "LA150C_RDIVER_V1.00"
ROOT_UUID = k.make_uuid("root", PROJECT_NAME)
STEM = "SCH_LA150C_MCU_V1.00"
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
        power_base=500,
        flag_base=500,
        power_rotation=0,
    )
    sheet.text(
        "title",
        "LA150C RDIVER V1.00 - MCU\nGD32F503REL7 BGA-64：8MHz 外部谐振器 / 512KB Flash / TIMER7 三相 PWM / 3×ADC / SPI2 / CAN FD / SWD",
        20.32,
        15.24,
        1.5,
    )

    pwr = 500

    def power(net: str, x: float, y: float, rotation: float = 0) -> None:
        nonlocal pwr
        pwr += 1
        sheet.power(f"{P}:{net}", f"#PWR{pwr:03d}", x, y, rotation)

    u = f"{P}:GD32F503REL7"
    ux, uy = 152.4, 100.33
    # The drawing sheet owns x >= 108 / y >= 165 for its title block, so the
    # main block stops above it and the clock network moves to the left.
    sheet.block("G  GD32F503REL7 主控", 99.06, 41.91, 205.74, 160.02)
    sheet.component(u, "U1", "GD32F503REL7", ux, uy, footprint="", description="Cortex-M33 MCU BGA-64")

    def up(n):
        return sheet.pin(u, ux, uy, 0, n)

    # ------------------------------------------------------------------ ports
    LEFT_PORTS = {
        "H5": ("SO_A", "input"), "H2": ("SO_B", "input"),
        "H3": ("SO_C", "input"),
        "A4": ("FORCE_P", "input"), "A3": ("FORCE_N", "input"),
        "H6": ("AD_VBUS", "input"), "H7": ("AD_NTC", "input"),
        "G8": ("CANFD_RX", "input"), "G6": ("CANFD_TX", "output"),
    }
    RIGHT_PORTS = {
        "F6": ("PWM_A", "output"), "C1": ("nSLEEP", "output"),
        "D1": ("nFAULT", "input"), "C8": ("PWM_B", "output"),
        "B8": ("PWM_C", "output"), "C7": ("SWDIO", "bidirectional"),
        "C6": ("SWCLK", "input"), "A5": ("SPI2_SCK", "output"),
        "A7": ("SPI2_CSN", "output"), "B6": ("SPI2_MISO", "input"),
    }

    for number, (net, shape) in LEFT_PORTS.items():
        point = up(number)
        sheet.wire(point[0], point[1], 110.49, point[1])
        sheet.hier_label(net, 110.49, point[1], shape=shape, rotation=180)
    for number, (net, shape) in RIGHT_PORTS.items():
        point = up(number)
        sheet.wire(point[0], point[1], 196.85, point[1])
        sheet.hier_label(net, 196.85, point[1], shape=shape, rotation=0)

    # ------------------------------------------------------- VDD / VDDA rails
    digital_sources = ("C2", "A1", "A8", "H1", "H8")
    digital_rail_y = 57.15
    digital_points = [up(n) for n in digital_sources]
    sheet.wire(83.82, digital_rail_y, digital_points[-1][0], digital_rail_y)
    power("PWR_3V3", 83.82, 52.07)
    sheet.wire(83.82, 52.07, 83.82, digital_rail_y)
    for point in digital_points:
        sheet.wire(point[0], point[1], point[0], digital_rail_y)
        sheet.junction(point[0], digital_rail_y)
    for index, (refc, val, desc) in enumerate(
        (
            ("C33", "10uF", "0603 10uF 10V X7R 体电容"),
            ("C32", "100nF", "0201 100nF 16V VBAT 去耦"),
            ("C28", "100nF", "0201 100nF 16V VDD 去耦"),
            ("C29", "100nF", "0201 100nF 16V VDD 去耦"),
            ("C30", "100nF", "0201 100nF 16V VDD 去耦"),
            ("C31", "100nF", "0201 100nF 16V VDD 去耦"),
        )
    ):
        # 7.62 mm pitch keeps the Reference / Value text of adjacent parts apart
        x = 83.82 + index * 7.62
        sheet.component("Device:C", refc, val, x, 62.23, footprint="", description=desc)
        top = sheet.pin("Device:C", x, 62.23, 0, "1")
        bot = sheet.pin("Device:C", x, 62.23, 0, "2")
        sheet.wire(x, digital_rail_y, top[0], top[1])
        sheet.junction(x, digital_rail_y)
        sheet.wire(bot[0], bot[1], bot[0], 68.58)
    sheet.wire(83.82, 68.58, 121.92, 68.58)
    power("GND", 83.82, 68.58)
    sheet.junction(83.82, 68.58)
    for index in range(1, 6):
        sheet.junction(83.82 + index * 7.62, 68.58)

    # analog supply
    ana_rail_y = 52.07
    vdda = up("G1")
    sheet.wire(vdda[0], vdda[1], vdda[0], ana_rail_y)
    sheet.wire(vdda[0], ana_rail_y, 171.45, ana_rail_y)
    power("PWR_3V3A", 158.75, 44.45)
    sheet.wire(158.75, 44.45, 158.75, ana_rail_y)
    sheet.junction(158.75, ana_rail_y)
    for refc, val, desc, x in (
        ("C34", "100nF", "0201 100nF 16V VDDA", 163.83),
        ("C35", "1uF", "0402 1uF 10V VDDA", 171.45),
    ):
        sheet.component("Device:C", refc, val, x, 55.88, footprint="", description=desc)
        top = sheet.pin("Device:C", x, 55.88, 0, "1")
        bot = sheet.pin("Device:C", x, 55.88, 0, "2")
        sheet.junction(x, ana_rail_y)
        sheet.wire(bot[0], bot[1], bot[0], 62.23)
    sheet.wire(163.83, 62.23, 171.45, 62.23)
    power("AGND", 163.83, 62.23)
    sheet.junction(163.83, 62.23)
    sheet.text(
        "note:vdd",
        "VDD 4×100nF + 10µF；VBAT 100nF；VDDA 100nF + 1µF",
        99.06,
        48.26,
        1.27,
    )

    # --------------------------------------------------- ground / reset / boot
    vss_points = [up(n) for n in ("B2", "B7", "G2", "G7")]
    vssa = up("F2")
    gnd_rail_y = 142.24
    for point in vss_points:
        sheet.wire(point[0], point[1], point[0], gnd_rail_y)
    sheet.wire(vss_points[0][0], gnd_rail_y, vss_points[-1][0], gnd_rail_y)
    for point in vss_points[1:]:
        sheet.junction(point[0], gnd_rail_y)
    power("GND", vss_points[0][0], gnd_rail_y)
    sheet.junction(vss_points[0][0], gnd_rail_y)
    sheet.wire(vssa[0], vssa[1], vssa[0], gnd_rail_y)
    power("AGND", vssa[0], gnd_rail_y)

    # NRST: pull-up + 100nF + port (routed left, away from the VSS bank)
    nrst = up("D2")
    boot0 = up("B3")
    node_y = 148.59
    sheet.wire(nrst[0], nrst[1], nrst[0], node_y)
    sheet.wire(nrst[0], node_y, 110.49, node_y)
    sheet.hier_label("NRST", 110.49, node_y, shape="bidirectional", rotation=180)
    sheet.component("Device:R", "R33", "10K", 127.0, 144.78, footprint="", description="0201 10K 1%")
    r33_a = sheet.pin("Device:R", 127.0, 144.78, 0, "1")
    r33_b = sheet.pin("Device:R", 127.0, 144.78, 0, "2")
    power("PWR_3V3", r33_a[0], 137.16)
    sheet.wire(r33_a[0], 137.16, r33_a[0], r33_a[1])
    sheet.junction(r33_b[0], node_y)
    sheet.component("Device:C", "C36", "100nF", 116.84, 152.4, footprint="", description="0201 100nF 16V")
    c36_a = sheet.pin("Device:C", 116.84, 152.4, 0, "1")
    c36_b = sheet.pin("Device:C", 116.84, 152.4, 0, "2")
    sheet.junction(c36_a[0], node_y)
    sheet.wire(c36_b[0], c36_b[1], c36_b[0], 160.02)
    power("GND", c36_b[0], 160.02)
    sheet.text("note:nrst", "NRST：R33 10k 上拉 + C36 100nF；NRST 同时是 Bootloader 入口", 99.06, 156.21, 1.27)

    # BOOT0 / BOOT1 -> 10k pulldown.
    boot1 = up("H4")
    sheet.component("Device:R", "R37", "10K", boot0[0], 160.02, footprint="",
                    description="0201 10K 1% BOOT0 pull-down")
    r37_a = sheet.pin("Device:R", boot0[0], 160.02, 0, "1")
    r37_b = sheet.pin("Device:R", boot0[0], 160.02, 0, "2")
    sheet.wire(boot0[0], boot0[1], r37_a[0], r37_a[1])
    power("GND", r37_b[0], r37_b[1])
    sheet.wire(boot1[0], boot1[1], 110.49, boot1[1])
    sheet.label("BOOT1", 110.49, boot1[1], rotation=180)
    sheet.component("Device:R", "R38", "10K", 180.34, 156.21, footprint="",
                    description="0201 10K 1% BOOT1 pull-down")
    r38_a = sheet.pin("Device:R", 180.34, 156.21, 0, "1")
    r38_b = sheet.pin("Device:R", 180.34, 156.21, 0, "2")
    sheet.label("BOOT1", r38_a[0], r38_a[1])
    power("GND", r38_b[0], r38_b[1])
    sheet.text("note:boot", "BOOT0 / BOOT1 均经 10K 下拉到 GND = 主 Flash 启动", 160.02, 142.24, 1.27)

    # ------------------------------------ external-driver 8 MHz resonator
    osc_in, osc_out = up("E1"), up("F1")
    sheet.wire(osc_in[0], osc_in[1], osc_in[0], 142.24)
    sheet.label("OSC_IN", osc_in[0], 142.24)
    sheet.wire(osc_out[0], osc_out[1], osc_out[0], 142.24)
    sheet.label("OSC_OUT", osc_out[0], 142.24)

    sheet.block("H  8MHz 外部谐振器 (CSTNE8M00G52A000R0)", 55.88, 163.83, 127.0, 190.5)
    y1 = f"{P}:CSTNE8M00G52A000R0"
    yx, yy = 81.28, 185.42
    sheet.component(
        y1,
        "Y1",
        "CSTNE8M00G52A000R0",
        yx,
        yy,
        footprint="",
        description="External-driver 8MHz resonator, 10pF built-in, SMD3213-3P",
    )
    y1_1 = sheet.pin(y1, yx, yy, 0, "1")
    y1_2 = sheet.pin(y1, yx, yy, 0, "2")
    y1_3 = sheet.pin(y1, yx, yy, 0, "3")
    sheet.wire(y1_1[0], y1_1[1], 66.04, y1_1[1])
    sheet.label("OSC_IN", 66.04, y1_1[1], rotation=180)
    sheet.wire(y1_2[0], y1_2[1], 66.04, y1_2[1])
    power("GND", 66.04, y1_2[1])
    sheet.wire(y1_3[0], y1_3[1], 66.04, y1_3[1])
    sheet.label("OSC_OUT", 66.04, y1_3[1], rotation=180)
    sheet.text(
        "note:osc",
        "★ 时钟采用外置驱动器同款 CSTNE8M00G52A000R0：8MHz、内置 10pF、SMD3213-3P；"
        " pin1→OSCIN(E1)，pin3→OSCOUT(F1)，pin2→GND。",
        127.0,
        168.91,
        1.27,
    )
    sheet.text(
        "note:swd",
        "SWD（PA13/PA14 + NRST）是 φ13 内唯一调试/烧录通道，必须在 PCB 上保留可接入焊盘；SWD 排针放在 TOP 页",
        16.51,
        154.94,
        1.27,
    )

    # --------------------------------------------------------- unused pins
    used_balls = (
        set(LEFT_PORTS)
        | set(RIGHT_PORTS)
        | {"C2", "A1", "A8", "H1", "H8", "G1",
           "B2", "B7", "G2", "G7", "F2", "D2", "B3", "H4", "E1", "F1"}
    )
    for number in sheet.libraries.pin_numbers(u):
        if number not in used_balls:
            point = up(number)
            sheet.no_connect(point[0], point[1])

    sheet.write()
    print(f"wrote {sheet.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
