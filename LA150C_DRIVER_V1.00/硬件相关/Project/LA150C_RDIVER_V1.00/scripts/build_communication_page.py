#!/usr/bin/env python3
"""Build the LA150C communication sheet (CAN FD only).

Mechanical-space revision: remove the CMC and the 60.2R / 4.7nF split
termination.  Only the TCAN3413DDFR, its decoupling, connector-side ESD and
the CANH/CANL hierarchical ports remain.
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
        "LA150C RDIVER V1.00 - COMMUNICATION\n"
        "CAN FD：仲裁段 1Mbit/s，数据段 5Mbit/s；TCAN3413DDFR + DE5VS06BA",
        20.32,
        15.24,
        1.5,
    )
    sheet.block("F  CAN FD 收发器 TCAN3413DDFR", 22.86, 24.13, 223.52, 132.08)

    u = f"{P}:TCAN3413DDFR"
    ux, uy = 86.36, 78.74
    sheet.component(
        u,
        "U3",
        "TCAN3413DDFR",
        ux,
        uy,
        footprint="",
        description="CAN FD transceiver, 3.3V, SOT-23-8",
    )

    def up(n: str) -> tuple[float, float]:
        return sheet.pin(u, ux, uy, 0, n)

    txd, gnd, vcc, rxd = up("1"), up("2"), up("3"), up("4")
    stb, canh, canl, vio = up("8"), up("7"), up("6"), up("5")

    # MCU-side nets: QS01 resource mapping is PB13 = CANFD_TX, PB12 = CANFD_RX.
    sheet.wire(txd[0], txd[1], 57.15, txd[1])
    sheet.hier_label("CANFD_TX", 57.15, txd[1], shape="input", rotation=180)
    sheet.wire(rxd[0], rxd[1], 57.15, rxd[1])
    sheet.hier_label("CANFD_RX", 57.15, rxd[1], shape="output", rotation=180)

    # Local supply and decoupling.
    sheet.power(f"{P}:PWR_3V3", "#PWR301", vcc[0], vcc[1])
    sheet.power(f"{P}:PWR_3V3", "#PWR302", vio[0], vio[1])
    sheet.component("Device:C", "C13", "100nF", 60.96, 67.31, footprint="",
                    description="0201 100nF 16V")
    c13_a = sheet.pin("Device:C", 60.96, 67.31, 0, "1")
    c13_b = sheet.pin("Device:C", 60.96, 67.31, 0, "2")
    sheet.power(f"{P}:PWR_3V3", "#PWR303", c13_a[0], c13_a[1])
    sheet.wire(c13_b[0], c13_b[1], c13_b[0], 74.93)
    sheet.power(f"{P}:GND", "#PWR304", c13_b[0], 74.93)

    # STB low = normal mode; each ground return is local.
    sheet.power(f"{P}:GND", "#PWR305", gnd[0], gnd[1])
    sheet.power(f"{P}:GND", "#PWR306", stb[0], stb[1])
    sheet.text("note:stb", "STB(8) 接 GND = 正常工作模式；高电平为待机。", 22.86, 48.26, 1.27)

    # Connector-side CAN pair.  No CMC and no onboard split termination are
    # fitted in this mechanical revision.
    bus_start = 127.0
    sheet.wire(canh[0], canh[1], bus_start, canh[1])
    sheet.wire(canl[0], canl[1], bus_start, canl[1])

    d1 = f"{P}:DE5VS06BA"
    d2 = f"{P}:DE5VS06BA"
    sheet.component(d1, "D1", "DE5VS06BA", 154.94, 74.93, rotation=90, footprint="",
                    description="DFN0603 5V/60W CANH ESD protection")
    sheet.component(d2, "D2", "DE5VS06BA", 154.94, 88.9, rotation=90, footprint="",
                    description="DFN0603 5V/60W CANL ESD protection")
    d1_a = sheet.pin(d1, 154.94, 74.93, 90, "1")
    d1_b = sheet.pin(d1, 154.94, 74.93, 90, "2")
    d2_a = sheet.pin(d2, 154.94, 88.9, 90, "1")
    d2_b = sheet.pin(d2, 154.94, 88.9, 90, "2")
    sheet.wire(d1_a[0], d1_a[1], d1_a[0], canh[1])
    sheet.junction(d1_a[0], canh[1])
    sheet.wire(d1_b[0], d1_b[1], d1_b[0], 64.77)
    sheet.power(f"{P}:GND", "#PWR307", d1_b[0], 64.77, rotation=180)
    sheet.wire(d2_b[0], d2_b[1], d2_b[0], canl[1])
    sheet.junction(d2_b[0], canl[1])
    sheet.wire(d2_a[0], d2_a[1], d2_a[0], 96.52)
    sheet.power(f"{P}:GND", "#PWR308", d2_a[0], 96.52)

    sheet.hier_label("CANH", 210.82, canh[1], shape="bidirectional", rotation=0)
    sheet.hier_label("CANL", 210.82, canl[1], shape="bidirectional", rotation=0)
    sheet.wire(bus_start, canh[1], 210.82, canh[1])
    sheet.wire(bus_start, canl[1], 210.82, canl[1])

    sheet.text(
        "note:bus",
        "因板空间受限，本版取消 CMC 与板内 60.2Ω/4.7nF 分裂终端；"
        "总线段终端由线缆/系统端实现。D1/D2 靠近 J2 接口放置。",
        22.86,
        112.395,
        1.27,
    )

    sheet.write()
    print(f"wrote {sheet.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
