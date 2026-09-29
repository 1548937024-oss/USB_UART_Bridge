#!/usr/bin/env python3
"""Build the MicroDriver V2.10 communication sheet.

CAN FD section (U4 TCAN3413) plus RS485 section (U5 TPT481L1-DF6R), matching
PRJ_MicroDriver_V2.10.pdf page 4.  Every wire endpoint comes from Sheet.pin().
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "MicroDriver_V2.10"
ROOT_UUID = k.make_uuid("root", PROJECT_NAME)
STEM = "SCH_MicroDriver_V2.10_communication"
P = PROJECT_NAME

U4 = f"{P}:TCAN3413DDFR"
U5 = f"{P}:TPT481L1-DF6R"
ESD = f"{P}:PESD1CAN,215"


def main() -> int:
    lib = PROJECT_ROOT / "library" / f"{PROJECT_NAME}.kicad_sym"
    libraries = k.Libraries()
    libraries.register("power", lib)
    libraries.register(PROJECT_NAME, lib)
    libraries.register("Device", Path(r"D:\KiCad10.0\share\kicad\symbols\Device.kicad_sym"))

    sheet = k.Sheet(
        path=PROJECT_ROOT / f"{STEM}.kicad_sch",
        project=PROJECT_NAME,
        uuid_key=STEM,
        libraries=libraries,
        root_uuid=ROOT_UUID,
        sheet_uuid=k.make_uuid("sheet", STEM),
        power_base=400,
        flag_base=400,
        power_rotation=180,
    )
    sheet.text("title", "MicroDriver V2.10 - communication\nCAN FD（TCAN3413）与 RS485（TPT481L1）", 20.32, 17.78, 1.5)

    pwr = 400

    def gnd(x, y):
        nonlocal pwr
        sheet.power("power:GND_POWER_GROUND", f"#PWR{pwr:02d}", x, y)
        pwr += 1

    def rail(x, y):
        nonlocal pwr
        sheet.power("power:+3.3V_BAR", f"#PWR{pwr:02d}", x, y)
        pwr += 1

    # ------------------------------------------------------------ CAN FD
    sheet.block("CAN FD - U4 TCAN3413", 19.05, 25.4, 180.34, 96.52)
    u4x, u4y = 76.2, 60.96
    sheet.component(U4, "U4", "TCAN3413DDFR", u4x, u4y, footprint="",
                    description="CAN FD 收发器 TSOT-23-8")

    def u4p(n):
        return sheet.pin(U4, u4x, u4y, 0, n)

    txd, gnd4, vcc4, rxd = u4p("1"), u4p("2"), u4p("3"), u4p("4")
    stb, canh, canl, vio = u4p("8"), u4p("7"), u4p("6"), u4p("5")

    sheet.hier_label("CANFD-TX", txd[0] - 25.4, txd[1], shape="input", rotation=180)
    sheet.wire(txd[0] - 25.4, txd[1], txd[0], txd[1])
    sheet.hier_label("CANFD-RX", rxd[0] - 25.4, rxd[1], shape="output", rotation=180)
    sheet.wire(rxd[0] - 25.4, rxd[1], rxd[0], rxd[1])

    # Decoupling caps sit OUTSIDE the pin-row x range (left of the label
    # column / right of the body) so their vertical drops cannot land on
    # another net's wire.  See docs/V2.10_绘制规则.md.
    for ref, pin, x in (("C30", vcc4, 30.48), ("C31", vio, 106.68)):
        cy = pin[1] + 7.62
        sheet.component("Device:C", ref, "100nF", x, cy, footprint="",
                        description="0201 100nF 16V")
        top = sheet.pin("Device:C", x, cy, 0, "1")
        bot = sheet.pin("Device:C", x, cy, 0, "2")
        sheet.wire(pin[0], pin[1], x, pin[1])
        sheet.wire(x, pin[1], top[0], top[1])
        sheet.junction(x, pin[1])
        rail(x, pin[1])
        sheet.wire(bot[0], bot[1], bot[0], bot[1] + 5.08)
        gnd(bot[0], bot[1] + 5.08)

    # STB tied low (normal mode); each ground gets its own local symbol rather
    # than a long return wire that would cross the TXD/RXD rows.
    stb_x = stb[0] + 15.24
    sheet.wire(stb[0], stb[1], stb_x, stb[1])
    gnd(stb_x, stb[1])
    sheet.wire(gnd4[0], gnd4[1], gnd4[0] - 12.7, gnd4[1])
    gnd(gnd4[0] - 12.7, gnd4[1])

    bus_x = 152.4
    sheet.hier_label("CANH", bus_x, canh[1], shape="bidirectional", rotation=0)
    sheet.wire(canh[0], canh[1], bus_x, canh[1])
    sheet.hier_label("CANL", bus_x, canl[1], shape="bidirectional", rotation=0)
    sheet.wire(canl[0], canl[1], bus_x, canl[1])

    d6y = (canh[1] + canl[1]) / 2
    sheet.component(ESD, "D6", "PESD1CAN", 137.16, d6y, footprint="",
                    description="SOT23/24V/200W CAN ESD")
    d6a = sheet.pin(ESD, 137.16, d6y, 0, "1")
    d6b = sheet.pin(ESD, 137.16, d6y, 0, "2")
    d6c = sheet.pin(ESD, 137.16, d6y, 0, "3")
    sheet.wire(d6a[0], d6a[1], d6a[0], canl[1])
    sheet.wire(d6b[0], d6b[1], d6b[0], canh[1])
    sheet.wire(d6c[0], d6c[1], d6c[0], d6c[1] + 5.08)
    gnd(d6c[0], d6c[1] + 5.08)

    for ref, y, x in (("C29", canh[1], 124.46), ("C32", canl[1], 132.08)):
        sheet.component("Device:C", ref, "10pF", x, y + 8.89, footprint="",
                        description="0201 10pF 50V")
        top = sheet.pin("Device:C", x, y + 8.89, 0, "1")
        bot = sheet.pin("Device:C", x, y + 8.89, 0, "2")
        sheet.wire(x, y, top[0], top[1])
        sheet.junction(x, y)
        sheet.wire(bot[0], bot[1], bot[0], bot[1] + 5.08)
        gnd(bot[0], bot[1] + 5.08)
    sheet.text("note:can", "CANH/CANL：5 Mbps 差分总线，PCB 需差分走线并包地；D6 靠近接口放置", 25.4, 91.44)

    # ------------------------------------------------------------ RS485
    sheet.block("RS485 - U5 TPT481L1", 19.05, 106.68, 180.34, 190.5)
    u5x, u5y = 76.2, 146.05
    sheet.component(U5, "U5", "TPT481L1-DF6R", u5x, u5y, footprint="",
                    description="RS485 收发器 DFN-8L 3x3")

    def u5p(n):
        return sheet.pin(U5, u5x, u5y, 0, n)

    r_p, re_p, de_p, d_p, g5 = u5p("1"), u5p("2"), u5p("3"), u5p("4"), u5p("5")
    a_p, b_p, v5 = u5p("6"), u5p("7"), u5p("8")

    for net, pin, shape in (("RS485-RX", r_p, "output"), ("RS485-DIR", re_p, "input"),
                            ("RS485-TX", d_p, "input")):
        sheet.hier_label(net, pin[0] - 25.4, pin[1], shape=shape, rotation=180)
        sheet.wire(pin[0] - 25.4, pin[1], pin[0], pin[1])

    # RE and DE tied together, driven by RS485-DIR
    sheet.wire(re_p[0], re_p[1], re_p[0] - 5.08, re_p[1])
    sheet.wire(re_p[0] - 5.08, re_p[1], de_p[0] - 5.08, de_p[1])
    sheet.wire(de_p[0] - 5.08, de_p[1], de_p[0], de_p[1])
    sheet.junction(de_p[0] - 5.08, de_p[1])

    c33x = v5[0] + 12.7
    c33y = v5[1] - 3.81
    sheet.component("Device:C", "C33", "100nF", c33x, c33y, footprint="",
                    description="0201 100nF 16V")
    c33a = sheet.pin("Device:C", c33x, c33y, 0, "1")
    c33b = sheet.pin("Device:C", c33x, c33y, 0, "2")
    sheet.wire(v5[0], v5[1], c33x, v5[1])
    rail(c33x, v5[1])
    # C33 hangs upward so its pins stay clear of the B / ~RE rows below
    sheet.wire(c33a[0], c33a[1], c33a[0], c33a[1] - 5.08)
    gnd(c33a[0], c33a[1] - 5.08)

    sheet.wire(g5[0], g5[1], g5[0] - 12.7, g5[1])
    sheet.wire(g5[0] - 12.7, g5[1], g5[0] - 12.7, g5[1] + 7.62)
    gnd(g5[0] - 12.7, g5[1] + 7.62)
    pad = u5p("9")
    sheet.wire(pad[0], pad[1], pad[0], pad[1] + 5.08)
    gnd(pad[0], pad[1] + 5.08)

    bus_x5 = 152.4
    for ref, pin, net in (("R21", a_p, "RS485-A"), ("R22", b_p, "RS485-B")):
        rx = pin[0] + 12.7
        sheet.component("Device:R", ref, "10R", rx, pin[1], rotation=90, footprint="",
                        description="0201 10Ω 1%")
        ra = sheet.pin("Device:R", rx, pin[1], 90, "1")
        rb = sheet.pin("Device:R", rx, pin[1], 90, "2")
        sheet.wire(pin[0], pin[1], ra[0], ra[1])
        sheet.wire(rb[0], rb[1], bus_x5, rb[1])
        sheet.hier_label(net, bus_x5, rb[1], shape="bidirectional", rotation=0)

    mid_y = (a_p[1] + b_p[1]) / 2
    d7y = mid_y + 10.16
    sheet.component(ESD, "D7", "PESD1CAN", 139.7, d7y, footprint="",
                    description="SOT23/24V/200W ESD")
    d7a = sheet.pin(ESD, 139.7, d7y, 0, "1")
    d7b = sheet.pin(ESD, 139.7, d7y, 0, "2")
    d7c = sheet.pin(ESD, 139.7, d7y, 0, "3")
    tap = 124.46
    sheet.wire(a_p[0], a_p[1], tap, a_p[1])
    sheet.junction(tap, a_p[1])
    sheet.wire(tap, a_p[1], tap, d7a[1])
    sheet.wire(d7a[0], d7a[1], tap, d7a[1])
    sheet.wire(b_p[0], b_p[1], tap - 2.54, b_p[1])
    sheet.junction(tap - 2.54, b_p[1])
    sheet.wire(tap - 2.54, b_p[1], tap - 2.54, d7b[1])
    sheet.wire(d7b[0], d7b[1], tap - 2.54, d7b[1])
    sheet.wire(d7c[0], d7c[1], d7c[0], d7c[1] + 5.08)
    gnd(d7c[0], d7c[1] + 5.08)
    sheet.text("note:485", "RE/DE 并联由 RS485-DIR 控制；A/B 各串 10Ω，D7 靠近接口", 25.4, 185.42)

    sheet.write()
    print(f"wrote {sheet.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
