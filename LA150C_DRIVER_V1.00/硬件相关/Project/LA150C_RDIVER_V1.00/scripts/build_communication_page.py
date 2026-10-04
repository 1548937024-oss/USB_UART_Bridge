#!/usr/bin/env python3
"""Build the LA150C communication sheet (CAN FD only).

Hardware design doc §3.8: TCAN3413DDFR at 3.3 V, CAN0 on PB12/PB13,
no on-board 120R termination (footprint only, DNP), ESD protection at the
connector side.  RS485 is deliberately not drawn - LA150C dropped it.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "LA150C_RDIVER_V1.00"
ROOT_UUID = k.make_uuid("root", PROJECT_NAME)
STEM = "SCH_LA150C_communication_V1.00"
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
        power_base=300,
        flag_base=300,
        power_rotation=0,
    )
    sheet.text(
        "title",
        "LA150C RDIVER V1.00 - COMMUNICATION\nCAN FD：仲裁段 1Mbit/s，数据段 5Mbit/s；TCAN3413DDFR + PESD1CAN；板内 120Ω 不贴片",
        20.32,
        15.24,
        1.5,
    )
    sheet.block("F  CAN FD 收发器 TCAN3413DDFR", 22.86, 24.13, 261.62, 132.08)

    u = f"{P}:TCAN3413DDFR"
    ux, uy = 95.25, 80.01
    sheet.component(u, "U3", "TCAN3413DDFR", ux, uy, footprint="", description="CAN FD 收发器 SOT-23-8")

    def up(n):
        return sheet.pin(u, ux, uy, 0, n)

    txd, rxd = up("1"), up("4")
    canh, canl = up("7"), up("6")
    vcc, vio = up("3"), up("5")
    gnd, stb = up("2"), up("8")

    # MCU side
    sheet.wire(txd[0], txd[1], 66.04, txd[1])
    sheet.hier_label("CAN0_TX", 66.04, txd[1], shape="input", rotation=180)
    sheet.wire(rxd[0], rxd[1], 66.04, rxd[1])
    sheet.hier_label("CAN0_RX", 66.04, rxd[1], shape="output", rotation=180)

    # 3.3V rail over the transceiver
    rail_y = 64.77
    sheet.wire(85.09, rail_y, 96.52, rail_y)
    sheet.power(f"{P}:PWR_3V3", "#PWR301", 95.25, 59.69)
    sheet.wire(95.25, 59.69, 95.25, rail_y)
    sheet.junction(95.25, rail_y)
    sheet.wire(vcc[0], vcc[1], vcc[0], rail_y)
    sheet.junction(vcc[0], rail_y)
    sheet.wire(vio[0], vio[1], vio[0], rail_y)
    sheet.junction(vio[0], rail_y)
    sheet.component("Device:C", "C13", "100nF", 85.09, 68.58, footprint="", description="0402 100nF 16V")
    c13_a = sheet.pin("Device:C", 85.09, 68.58, 0, "1")
    c13_b = sheet.pin("Device:C", 85.09, 68.58, 0, "2")
    sheet.junction(c13_a[0], rail_y)
    sheet.wire(c13_b[0], c13_b[1], c13_b[0], 95.25)
    sheet.power(f"{P}:GND", "#PWR302", c13_b[0], 95.25)

    # ground and standby
    sheet.wire(gnd[0], gnd[1], gnd[0], 95.25)
    sheet.wire(stb[0], stb[1], stb[0], 95.25)
    sheet.wire(gnd[0], 95.25, stb[0], 95.25)
    sheet.power(f"{P}:GND", "#PWR303", gnd[0], 95.25)
    sheet.junction(gnd[0], 95.25)
    sheet.text("note:stb", "STB 内部上拉；接 GND = 正常工作模式（高电平为待机）", 101.6, 93.98, 1.27)

    # CAN bus with ESD protection
    sheet.wire(canh[0], canh[1], 147.32, canh[1])
    sheet.hier_label("CANH", 127.0, canh[1], shape="bidirectional", rotation=0)
    sheet.wire(canl[0], canl[1], 157.48, canl[1])
    sheet.hier_label("CANL", 127.0, canl[1], shape="bidirectional", rotation=0)

    d2 = f"{P}:PESD1CAN,215"
    d2x, d2y = 152.4, 88.9
    sheet.component(d2, "D2", "PESD1CAN,215", d2x, d2y, rotation=180, footprint="",
                    description="CAN 总线 ESD 保护 SOT-23-6")
    d2_1 = sheet.pin(d2, d2x, d2y, 180, "1")
    d2_2 = sheet.pin(d2, d2x, d2y, 180, "2")
    d2_3 = sheet.pin(d2, d2x, d2y, 180, "3")
    sheet.text("note:esd", "D2 PESD1CAN：连接器侧就近布置，±4kV 接触 / ±8kV 空气", 166.37, 88.9, 1.27)
    # pin 1 / pin 2 sit above the body, pin 3 below -> bus lands on the I/O
    # pins and ground drops straight down
    sheet.wire(157.48, canl[1], 157.48, d2_1[1])
    sheet.wire(d2_3[0], d2_3[1], d2_3[0], d2_3[1] + 2.54)
    sheet.power(f"{P}:GND", "#PWR304", d2_3[0], d2_3[1] + 2.54)

    # optional on-board termination, not fitted
    sheet.component("Device:R", "R11", "120R(DNP)", 175.26, 80.01, footprint="",
                    description="1206 120Ω 终端电阻，默认不贴片", dnp=True)
    r11_a = sheet.pin("Device:R", 175.26, 80.01, 0, "1")
    r11_b = sheet.pin("Device:R", 175.26, 80.01, 0, "2")
    sheet.wire(r11_a[0], r11_a[1], 182.88, r11_a[1])
    sheet.label("CANH", 182.88, r11_a[1])
    sheet.wire(r11_b[0], r11_b[1], 182.88, r11_b[1])
    sheet.label("CANL", 182.88, r11_b[1])
    sheet.text(
        "note:term",
        "★ R11 120Ω 默认不贴（DNP）：LA150C 不内置终端，由总线两端各一只 120Ω 承担。\n"
        "PCB 仅预留 1206 焊盘供调试装配。",
        140.97,
        98.43,
        1.27,
    )
    sheet.text(
        "note:onlycan",
        "LA150C 仅保留 CAN FD + CANopen CiA402，不保留 RS485（PB6/PB7 已改作一维力传感器预留输入）。",
        22.86,
        112.395,
        1.27,
    )
    sheet.write()
    print(f"wrote {sheet.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
