#!/usr/bin/env python3
"""Build the LA150C POWER sheet.

Blocks, from the hardware design doc §3.1 / §3.5:

* 输入保护与母线电容 - SMF16CA TVS clamp and a 10 uF / 25 V bulk cap;
* 同步降压 3.3V       - U1 SCT2230MLUAR with the datasheet's 3.3V/2A
  application circuit (10uF + 100nF input, 100nF BST, 31.6k/10.2k feedback,
  2 x 22uF + 100nF output);
* 母线电压检测         - 100k/10k divider + 100pF to AD_VBUS;
* 地网络星形连接       - PGND / AGND / GND joined at one point through 0R.

Rules applied (ported from MicroDriver V2.10):
  * one PWR_FLAG per net;
  * every branch that lands mid-wire gets a junction;
  * pin coordinates come from the library, never from a guessed transform;
  * supply symbols above, ground symbols below.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "LA150C_RDIVER_V1.00"
ROOT_UUID = k.make_uuid("root", PROJECT_NAME)
STEM = "SCH_LA150C_POWER_V1.00"
P = PROJECT_NAME


def main() -> int:
    lib = PROJECT_ROOT / "library" / f"{PROJECT_NAME}.kicad_sym"
    libraries = k.Libraries()
    libraries.register(PROJECT_NAME, lib)
    libraries.register("Device", Path(r"D:\KiCad10.0\share\kicad\symbols\Device.kicad_sym"))
    libraries.register(
        "Transistor_FET", Path(r"D:\KiCad10.0\share\kicad\symbols\Transistor_FET.kicad_sym")
    )

    sheet = k.Sheet(
        path=PROJECT_ROOT / f"{STEM}.kicad_sch",
        project=PROJECT_NAME,
        uuid_key=STEM,
        libraries=libraries,
        root_uuid=ROOT_UUID,
        sheet_uuid=k.make_uuid("sheet", STEM),
        power_base=100,
        flag_base=100,
        power_rotation=0,
    )

    sheet.text(
        "title",
        "LA150C RDIVER V1.00 - POWER\n母线 VBUS_IN(4.2~15V) → SMF16CA / 10µF → VBUS → SCT2230MLUAR 同步降压 → PWR_3V3",
        17.78,
        13.97,
        1.5,
    )

    pwr = 100

    def gnd(net: str, x: float, y: float, rotation: float = 0) -> None:
        nonlocal pwr
        pwr += 1
        sheet.power(f"{P}:{net}", f"#PWR{pwr:03d}", x, y, rotation)

    def ref() -> str:
        nonlocal pwr
        pwr += 1
        return f"#PWR{pwr:03d}"

    # ================================================== A 输入保护与母线电容
    sheet.block("A  输入保护与母线电容", 20.32, 24.13, 218.44, 78.74)
    sheet.text(
        "note:a",
        "D3 SMF16CA 双向 TVS（SOD-123FL / 16 V / 200 W）；C18 按空间优化删除，"
        " 母线储能由控制板承担，驱动板保留 C4 1µF/50V 本地旁路。",
        22.86,
        33.02,
        1.27,
    )

    # VBUS_IN rail
    sheet.power(f"{P}:VBUS", ref(), 33.02, 30.48)
    sheet.wire(33.02, 30.48, 33.02, 41.91)
    sheet.wire(33.02, 41.91, 127.0, 41.91)

    # D3 bus TVS, exact QS01/QS03 part
    d3 = f"{P}:SMF16CA"
    sheet.component(d3, "D3", "SMF16CA", 60.96, 49.53, rotation=90, footprint="",
                    description="SOD-123FL 16V/200W bidirectional TVS")
    d3_a = sheet.pin(d3, 60.96, 49.53, 90, "1")
    d3_b = sheet.pin(d3, 60.96, 49.53, 90, "2")
    sheet.wire(60.96, 41.91, d3_b[0], d3_b[1])
    sheet.junction(60.96, 41.91)
    sheet.wire(d3_a[0], d3_a[1], d3_a[0], 62.23)
    gnd("PGND", d3_a[0], 62.23)

    # VBUS after the TVS / bulk capacitor
    sheet.power(f"{P}:VBUS", ref(), 127.0, 30.48)
    sheet.wire(127.0, 30.48, 127.0, 41.91)
    sheet.junction(127.0, 41.91)

    # ================================================== B 同步降压 3.3V
    sheet.block("B  同步降压 3.3V - U5 SCT2230MLUAR", 20.32, 86.36, 218.44, 152.4)
    sheet.text(
        "note:b",
        "U5 按 datasheet Figure 8 (12V→3.3V/2A) 配置：R3 301k 使能分压、C6 100nF BST-SW、"
        "R4 31.6k / R5 10.2k 反馈、C7 10µF X7R + C9 100nF 输出（60mA/200mV 目标）",
        22.86,
        92.71,
        1.27,
    )
    sheet.text(
        "note:b2",
        "C7/C21 = GRM188Z71A106KA73D；C8 已删除；R4/R5 改 0201 封装；U5 EN 分压 R3=301k",
        22.86,
        95.25,
        1.27,
    )

    u1 = f"{P}:SCT2230MLUAR"
    u1x, u1y = 95.25, 119.38
    sheet.component(u1, "U5", "SCT2230MLUAR", u1x, u1y, footprint="", description="17V/2A 同步降压模块 7L ECLGA")

    def u1p(n):
        return sheet.pin(u1, u1x, u1y, 0, n)

    vin, en, bst, pgnd = u1p("6"), u1p("3"), u1p("4"), u1p("7")
    vout, fb, sw = u1p("1"), u1p("2"), u1p("5")

    # VBUS rail
    sheet.power(f"{P}:VBUS", ref(), 35.56, 96.52)
    sheet.wire(35.56, 96.52, 35.56, vin[1])
    sheet.wire(35.56, vin[1], vin[0], vin[1])

    # input capacitors
    for refc, val, desc, x in (
        ("C4", "1uF", "0603 1uF 50V X7R", 44.45),
        ("C5", "100nF", "0402 100nF 50V", 52.07),
    ):
        sheet.component("Device:C", refc, val, x, 124.46, footprint="", description=desc)
        top = sheet.pin("Device:C", x, 124.46, 0, "1")
        bot = sheet.pin("Device:C", x, 124.46, 0, "2")
        sheet.wire(x, vin[1], top[0], top[1])
        sheet.junction(x, vin[1])
        sheet.wire(bot[0], bot[1], bot[0], 133.35)
    sheet.wire(44.45, 133.35, 52.07, 133.35)
    gnd("PGND", 44.45, 133.35)
    sheet.junction(44.45, 133.35)

    # EN divider: VBUS -> R3 -> EN (internal 1M to GND)
    sheet.component("Device:R", "R3", "301K", 74.93, 118.11, rotation=90, footprint="", description="0402 301K 1%（料号待确认）")
    r3_a = sheet.pin("Device:R", 74.93, 118.11, 90, "1")
    r3_b = sheet.pin("Device:R", 74.93, 118.11, 90, "2")
    sheet.wire(68.58, vin[1], 68.58, en[1])
    sheet.junction(68.58, vin[1])
    sheet.wire(68.58, en[1], r3_a[0], r3_a[1])
    sheet.wire(r3_b[0], r3_b[1], en[0], en[1])

    # BST capacitor between BST and SW, routed below the body
    sheet.component("Device:C", "C6", "100nF", 96.52, 130.81, rotation=90, footprint="", description="0402 100nF 16V BST")
    c6_a = sheet.pin("Device:C", 96.52, 130.81, 90, "1")
    c6_b = sheet.pin("Device:C", 96.52, 130.81, 90, "2")
    sheet.wire(bst[0], bst[1], bst[0], 130.81)
    sheet.wire(bst[0], 130.81, c6_a[0], c6_a[1])
    sheet.wire(c6_b[0], c6_b[1], 110.49, 130.81)
    sheet.wire(110.49, 130.81, 110.49, sw[1])
    sheet.wire(110.49, sw[1], sw[0], sw[1])
    sheet.junction(sw[0], sw[1])

    # PWR_3V3 output rail and output capacitors
    sheet.wire(vout[0], vout[1], 163.83, vout[1])
    sheet.power(f"{P}:PWR_3V3", ref(), 163.83, 110.49)
    sheet.wire(163.83, vout[1], 163.83, 110.49)
    sheet.junction(163.83, vout[1])
    for refc, val, desc, x in (
        ("C7", "10uF", "0603 10uF 10V X7R", 121.92),
        ("C9", "100nF", "0402 100nF 16V", 142.24),
    ):
        sheet.component("Device:C", refc, val, x, 121.92, footprint="", description=desc)
        top = sheet.pin("Device:C", x, 121.92, 0, "1")
        bot = sheet.pin("Device:C", x, 121.92, 0, "2")
        sheet.wire(x, vout[1], top[0], top[1])
        sheet.junction(x, vout[1])
        sheet.wire(bot[0], bot[1], bot[0], 130.81)
    sheet.wire(121.92, 130.81, 142.24, 130.81)
    gnd("PGND", 121.92, 130.81)
    sheet.junction(121.92, 130.81)

    # feedback divider, joined to the FB pin by a labelled stub to keep the
    # VOUT rail and the output capacitors crossing-free
    sheet.wire(fb[0], fb[1], 116.84, fb[1])
    sheet.label("U1_FB", 116.84, fb[1])
    sheet.component(
        "Device:R",
        "R4",
        "31.6K",
        175.26,
        105.41,
        footprint="Resistors:R_0201_0603Metric",
        description="0201 31.6K 1%（料号待确认）",
    )
    sheet.component(
        "Device:R",
        "R5",
        "10.2K",
        175.26,
        115.57,
        footprint="Resistors:R_0201_0603Metric",
        description="0201 10.2K 1%（料号待确认）",
    )
    r4_a = sheet.pin("Device:R", 175.26, 105.41, 0, "1")
    r4_b = sheet.pin("Device:R", 175.26, 105.41, 0, "2")
    r5_a = sheet.pin("Device:R", 175.26, 115.57, 0, "1")
    r5_b = sheet.pin("Device:R", 175.26, 115.57, 0, "2")
    sheet.wire(r4_a[0], r4_a[1], r4_a[0], 99.06)
    sheet.power(f"{P}:PWR_3V3", ref(), r4_a[0], 99.06)
    sheet.wire(r4_b[0], r4_b[1], r5_a[0], r5_a[1])
    sheet.junction(r4_b[0], 110.49)
    sheet.wire(r4_b[0], 110.49, 182.88, 110.49)
    sheet.label("U1_FB", 182.88, 110.49, rotation=180)
    sheet.wire(r5_b[0], r5_b[1], r5_b[0], 121.92)
    gnd("PGND", r5_b[0], 121.92)

    # U1 PGND
    sheet.wire(pgnd[0], pgnd[1], 113.03, pgnd[1])
    sheet.wire(113.03, pgnd[1], 113.03, 133.35)
    gnd("PGND", 113.03, 133.35)

    # ================================================== C 母线电压检测
    sheet.block("C  母线电压检测 → AD_VBUS", 20.32, 157.48, 127.0, 198.12)
    sheet.text(
        "note:c",
        "分压比 1/11：8V→0.727V，14V→1.273V，16V→1.455V；RC 由 100k‖10k × 100pF ≈ 0.91µs",
        22.86,
        162.56,
        1.27,
    )
    sheet.component("Device:R", "R6", "100K", 35.56, 175.26, footprint="", description="0402 100K 1%")
    sheet.component("Device:R", "R7", "10K", 35.56, 185.42, footprint="", description="0201 10K 1%")
    r6_a = sheet.pin("Device:R", 35.56, 175.26, 0, "1")
    r6_b = sheet.pin("Device:R", 35.56, 175.26, 0, "2")
    r7_a = sheet.pin("Device:R", 35.56, 185.42, 0, "1")
    r7_b = sheet.pin("Device:R", 35.56, 185.42, 0, "2")
    sheet.power(f"{P}:VBUS", ref(), r6_a[0], 166.37)
    sheet.wire(r6_a[0], 166.37, r6_a[0], r6_a[1])
    sheet.wire(r6_b[0], r6_b[1], r7_a[0], r7_a[1])
    sheet.junction(r6_b[0], 180.34)
    sheet.wire(r6_b[0], 180.34, 63.5, 180.34)
    sheet.hier_label("AD_VBUS", 63.5, 180.34, shape="output", rotation=0)
    sheet.component("Device:C", "C10", "100pF", 45.72, 186.69, footprint="",
                    description="0201 100pF 50V C0G")
    c10_a = sheet.pin("Device:C", 45.72, 186.69, 0, "1")
    c10_b = sheet.pin("Device:C", 45.72, 186.69, 0, "2")
    sheet.wire(45.72, 180.34, c10_a[0], c10_a[1])
    sheet.junction(45.72, 180.34)
    sheet.wire(r7_b[0], r7_b[1], r7_b[0], 190.5)
    sheet.wire(r7_b[0], 190.5, c10_b[0], 190.5)
    gnd("AGND", r7_b[0], 190.5)
    sheet.junction(r7_b[0], 190.5)

    # ================================================== D 地网络星形连接
    sheet.block("D  地网络星形连接", 233.68, 86.36, 276.86, 152.4)
    sheet.text(
        "note:d",
        "PGND / AGND / GND 各经 0Ω 在单点汇合\n（芯片地星形连接，避免大电流回流污染采样参考）",
        236.22,
        93.98,
        1.27,
    )
    star_y = 120.65
    sheet.wire(241.3, star_y, 264.16, star_y)
    for refc, x, net in (
        ("R8", 252.73, "GND"),
        ("R9", 241.3, "PGND"),
        ("R10", 264.16, "AGND"),
    ):
        sheet.component("Device:R", refc, "0R", x, 124.46, footprint="", description="0402 0R 1%")
        top = sheet.pin("Device:R", x, 124.46, 0, "1")
        bot = sheet.pin("Device:R", x, 124.46, 0, "2")
        if top[1] != star_y:
            sheet.wire(x, star_y, top[0], top[1])
        sheet.wire(bot[0], bot[1], bot[0], 133.35)
        gnd(net, bot[0], 133.35)
    sheet.junction(252.73, star_y)

    # One PWR_FLAG per ground net.  GND is flagged on the TOP sheet at the
    # external connector, so it is not repeated here.
    for refc, x, net in (("R9", 241.3, "PGND"), ("R10", 264.16, "AGND")):
        sheet.pwr_flag(x, 129.54)
        sheet.junction(x, 129.54)

    # VBUS is driven only through the P-MOS (passive), so it needs a flag here;
    # VBUS_IN is flagged on the TOP sheet at connector J1.

    sheet.write()
    print(f"wrote {sheet.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
