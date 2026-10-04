#!/usr/bin/env python3
"""Build the LA150C MCU sheet (GD32F503REL7, LQFP-64).

Hardware design doc §3.2 / §4.1: 8 MHz resonator on OSCIN/OSCOUT, SWD on
PA13/PA14/NRST, VDD bank + VDDA/VREFP decoupling, BOOT0 tied low.  Every pin
that is not used gets an explicit no-connect marker.
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
        "LA150C RDIVER V1.00 - MCU\nGD32F503REL7 LQFP-64：168MHz / 512KB Flash / TIMER7 三相 PWM / 3×ADC 注入组 / SPI2 / CAN0 / SWD",
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
    sheet.component(u, "U1", "GD32F503REL7", ux, uy, footprint="", description="Cortex-M4F MCU LQFP-64")

    def up(n):
        return sheet.pin(u, ux, uy, 0, n)

    # ------------------------------------------------------------------ ports
    LEFT_PORTS = {
        "14": ("SO_A", "input"), "17": ("SO_B", "input"),
        "21": ("SPI2_SCK", "output"), "22": ("SPI2_MISO", "input"),
        "23": ("SO_C", "input"),
        "58": ("FORCE_P", "input"), "59": ("FORCE_N", "input"),
        "29": ("AD_VBUS", "input"), "30": ("AD_NTC", "input"),
        "33": ("CAN0_RX", "input"), "34": ("CAN0_TX", "output"),
        "8": ("EN_B", "output"), "9": ("EN_C", "output"), "10": ("PWM_C", "output"),
    }
    RIGHT_PORTS = {
        "39": ("PWM_A", "output"), "3": ("nSLEEP", "output"),
        "4": ("nFAULT", "input"), "44": ("EN_A", "output"),
        "45": ("PWM_B", "output"), "46": ("SWDIO", "bidirectional"),
        "49": ("SWCLK", "input"), "55": ("SPI2_CSN", "output"),
    }
    LEFT_USED = set(LEFT_PORTS)
    RIGHT_USED = set(RIGHT_PORTS)

    for number, (net, shape) in LEFT_PORTS.items():
        point = up(number)
        sheet.wire(point[0], point[1], 110.49, point[1])
        sheet.hier_label(net, 110.49, point[1], shape=shape, rotation=180)
    for number, (net, shape) in RIGHT_PORTS.items():
        point = up(number)
        sheet.wire(point[0], point[1], 196.85, point[1])
        sheet.hier_label(net, 196.85, point[1], shape=shape, rotation=0)

    # ------------------------------------------------------- VDD / VDDA rails
    digital_sources = ("1", "19", "32", "48", "64")
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
            ("C33", "10uF", "0805 10uF 16V 体电容"),
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
    vdda = up("13")
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
    vss_points = [up(n) for n in ("18", "31", "47", "63")]
    vssa = up("12")
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
    nrst = up("7")
    boot0 = up("60")
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

    # BOOT0 -> GND
    sheet.wire(boot0[0], boot0[1], boot0[0], 156.21)
    power("GND", boot0[0], 156.21)
    sheet.text("note:boot", "BOOT0 接 GND = 从主 Flash 启动", 160.02, 154.94, 1.27)

    # ------------------------------------------------ 8 MHz resonator network
    pd0, pd1 = up("5"), up("6")
    sheet.block("H  8MHz 时钟 (CSTCE8M00G52-R0)", 55.88, 163.83, 104.14, 190.5)
    osc_y = 176.53
    sheet.wire(pd0[0], pd0[1], pd0[0], 161.29)
    sheet.wire(pd0[0], 161.29, 72.39, 161.29)
    sheet.wire(72.39, 161.29, 72.39, osc_y)
    sheet.wire(pd1[0], pd1[1], pd1[0], 163.83)
    sheet.wire(pd1[0], 163.83, 90.17, 163.83)
    sheet.wire(90.17, 163.83, 90.17, osc_y)
    x1 = f"{P}:CSTCE8M00G52-R0"
    sheet.component(x1, "X1", "CSTCE8M00G52-R0", 81.28, osc_y, footprint="",
                    description="8MHz 三端陶瓷谐振器 SMD-3225")
    x1_a = sheet.pin(x1, 81.28, osc_y, 0, "1")
    x1_b = sheet.pin(x1, 81.28, osc_y, 0, "3")
    x1_g = sheet.pin(x1, 81.28, osc_y, 0, "2")
    sheet.junction(x1_a[0], osc_y)
    sheet.junction(x1_b[0], osc_y)
    sheet.wire(x1_g[0], x1_g[1], x1_g[0], 186.69)
    power("GND", x1_g[0], 186.69)
    for refc, val, x, side in (("C37", "10pF", 66.04, 1), ("C38", "10pF", 96.52, 2)):
        sheet.component("Device:C", refc, val, x, 180.34, footprint="",
                        description="0201 10pF 50V 谐振器负载")
        top = sheet.pin("Device:C", x, 180.34, 0, "1")
        bot = sheet.pin("Device:C", x, 180.34, 0, "2")
        sheet.wire(top[0], top[1], x1_a[0] if side == 1 else x1_b[0], osc_y)
        power("GND", bot[0], bot[1])
    sheet.text(
        "note:osc",
        "★ 时钟源冲突：hw 设计 §3.2.2 要求 ±10ppm，而 BOM 的 CSTCE8M00G52-R0 是陶瓷谐振器（±0.5%），须重新选型",
        16.51,
        152.4,
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
    for number in ("14", "15", "16", "17", "20", "26", "27", "28", "58", "59",
                   "29", "30", "33", "34", "35", "36", "8", "9", "10", "11", "24"):
        if number not in LEFT_USED and number != "60":
            point = up(number)
            sheet.no_connect(point[0], point[1])
    for number in ("25", "37", "38", "39", "40", "51", "52", "53", "2", "3", "4",
                   "41", "42", "43", "44", "45", "46", "49", "50", "55", "56",
                   "57", "61", "62"):
        if number not in RIGHT_USED:
            point = up(number)
            sheet.no_connect(point[0], point[1])
    pd2 = up("54")
    sheet.no_connect(pd2[0], pd2[1])

    sheet.write()
    print(f"wrote {sheet.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
