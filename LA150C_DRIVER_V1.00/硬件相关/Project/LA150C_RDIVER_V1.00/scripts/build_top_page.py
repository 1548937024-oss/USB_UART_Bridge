#!/usr/bin/env python3
"""Build the LA150C RDIVER V1.00 TOP (root) sheet.

The top sheet carries the five hierarchical sheets, the external 4-pin
DF52 connector, the SWD header, the motor/force test pads and the power flow
annotation.  Signals between adjacent blocks are drawn as straight wires;
the connector-side nets use short labelled stubs.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402
from ports import PORTS, SHEET_FILES, SHEET_PLACEMENT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "LA150C_RDIVER_V1.00"
ROOT_UUID = k.make_uuid("root", PROJECT_NAME)
P = PROJECT_NAME


def main() -> int:
    lib = PROJECT_ROOT / "library" / f"{PROJECT_NAME}.kicad_sym"
    libraries = k.Libraries()
    libraries.register(PROJECT_NAME, lib)
    libraries.register("Device", Path(r"D:\KiCad10.0\share\kicad\symbols\Device.kicad_sym"))
    libraries.register("Connector", Path(r"D:\KiCad10.0\share\kicad\symbols\Connector.kicad_sym"))

    power_counter = [900]

    def next_power() -> str:
        power_counter[0] += 1
        return f"#PWR{power_counter[0]:03d}"

    sheet = k.Sheet(
        path=PROJECT_ROOT / f"{PROJECT_NAME}.kicad_sch",
        project=PROJECT_NAME,
        uuid_key="root",
        uuid_value=ROOT_UUID,
        libraries=libraries,
        root_uuid=ROOT_UUID,
        page="1",
        power_base=900,
        flag_base=900,
        power_rotation=0,
    )

    # ------------------------------------------------------------- block pins
    # name -> (left pins, right pins); each pin is (net, y)
    PINS: dict[str, tuple[list[tuple[str, float]], list[tuple[str, float]]]] = {
        "POWER": ([], [("AD_VBUS", 45.72)]),
        "communication": (
            [],
            [("CANFD_TX", 71.12), ("CANFD_RX", 76.2), ("CANH", 81.28), ("CANL", 86.36)],
        ),
        "ENCODER": (
            [],
            [("SPI2_SCK", 111.76), ("SPI2_MISO", 116.84), ("SPI2_CSN", 121.92)],
        ),
        "MCU": (
            [
                ("AD_VBUS", 45.72), ("CANFD_TX", 71.12), ("CANFD_RX", 76.2),
                ("SPI2_SCK", 111.76), ("SPI2_MISO", 116.84), ("SPI2_CSN", 121.92),
                ("FORCE_P", 138.43), ("FORCE_N", 143.51),
                ("SWDIO", 148.59), ("SWCLK", 153.67), ("NRST", 158.75),
            ],
            [
                ("PWM_A", 30.48), ("PWM_B", 35.56), ("PWM_C", 40.64),
                ("nSLEEP", 45.72), ("nFAULT", 50.8),
                ("SO_A", 76.2), ("SO_B", 81.28), ("SO_C", 86.36), ("AD_NTC", 91.44),
            ],
        ),
        "MOTOR": (
            [
                ("PWM_A", 30.48), ("PWM_B", 35.56), ("PWM_C", 40.64),
                ("nSLEEP", 45.72), ("nFAULT", 50.8),
                ("SO_A", 76.2), ("SO_B", 81.28), ("SO_C", 86.36), ("AD_NTC", 91.44),
            ],
            [("MOT_U", 60.96), ("MOT_V", 66.04), ("MOT_W", 71.12)],
        ),
    }

    # ----------------------------------------------------------- hierarchical
    for name, (x, y, w, h) in SHEET_PLACEMENT.items():
        stem, page = SHEET_FILES[name]
        direction = dict(PORTS[name])
        left, right = PINS[name]
        pins = [
            (net, direction[net], x, py, 180) for net, py in left
        ] + [
            (net, direction[net], x + w, py, 0) for net, py in right
        ]
        sheet.subsheet(name, f"{stem}.kicad_sch", x, y, w, h,
                       k.make_uuid("sheet", stem), page, pins)

    # ------------------------------------ straight wires between adjacent blocks
    wires: list[tuple[str, tuple[float, float], tuple[float, float]]] = []

    def wire(net: str, a: tuple[float, float], b: tuple[float, float]) -> None:
        sheet.wire(a[0], a[1], b[0], b[1])
        wires.append((net, a, b))

    def label(net: str, x: float, y: float, rotation: float = 0) -> None:
        sheet.label(net, x, y, rotation=rotation)

    for name in ("POWER", "communication", "ENCODER"):
        x, y, w, h = SHEET_PLACEMENT[name]
        mcu_left_pins = dict(PINS["MCU"][0])
        for net, py in PINS[name][1]:
            if net in mcu_left_pins:
                wire(net, (x + w, py), (SHEET_PLACEMENT["MCU"][0], py))
            else:
                # connector-side net (CANH / CANL): short labelled stub
                wire(net, (x + w, py), (76.2, py))
                label(net, 76.2, py)

    mx, my, mw, mh = SHEET_PLACEMENT["MCU"]
    gx, gy, gw, gh = SHEET_PLACEMENT["MOTOR"]
    for net, py in PINS["MCU"][1]:
        wire(net, (mx + mw, py), (gx, py))

    # ------------------------------------------------ MOTOR phases -> test pads
    for net, py in PINS["MOTOR"][1]:
        wire(net, (gx + gw, py), (254.0, py))
        label(net, 254.0, py)

    # ------------------------------------------------- MCU service -> SWD header
    mcu_left = dict(PINS["MCU"][0])
    for net in ("FORCE_P", "FORCE_N", "SWDIO", "SWCLK", "NRST"):
        py = mcu_left[net]
        wire(net, (mx, py), (76.2, py))
        label(net, 76.2, py, rotation=180)

    swd = f"{P}:SWD-1X3-1.0"
    swd_x, swd_y = 45.72, 168.91
    sheet.component(swd, "J1", "SWD-1X3-1.0", swd_x, swd_y, footprint="",
                    description="1x3 1.0mm SWD header: SWDIO/SWCLK/GND")

    def swd_pin(n):
        return sheet.pin(swd, swd_x, swd_y, 0, n)

    swd_map = (
        ("1", "SWDIO", False), ("2", "GND", True), ("3", "SWCLK", False),
    )
    for number, net, is_power in swd_map:
        point = swd_pin(number)
        wire(net, (point[0], point[1]), (31.75, point[1]))
        if is_power:
            sheet.power(f"{P}:{net}", next_power(), 31.75, point[1])
        else:
            label(net, 31.75, point[1], rotation=180)

    # --------------------------------- external 4x 0.5mm solder holes (J2)
    j1 = f"{P}:SOLDER_HOLES_4P_0.5MM"
    j1_x, j1_y = 45.72, 149.86
    sheet.component(j1, "J2", "SOLDER_HOLES_4P_0.5MM", j1_x, j1_y, footprint="",
                    description="4x 0.5mm solder holes, 0.8mm pad, 2.54mm pitch")

    def j1_pin(n):
        return sheet.pin(j1, j1_x, j1_y, 0, n)

    for number, net, is_power, side in (
        ("1", "CANL", False, "left"), ("2", "CANH", False, "left"),
        ("3", "VBUS", True, "left"), ("4", "GND", True, "left"),
    ):
        point = j1_pin(number)
        endpoint = {"1": 31.75, "2": 31.75, "3": 27.94, "4": 26.67}[number]
        wire(net, (point[0], point[1]), (endpoint, point[1]))
        if is_power:
            sheet.power(f"{P}:{net}", next_power(), endpoint, point[1])
        else:
            label(net, endpoint, point[1], rotation=180 if side == "left" else 0)

    sheet.pwr_flag(27.94, j1_pin("3")[1])
    sheet.pwr_flag(26.67, j1_pin("4")[1])

    # ------------------------------------------- motor power solder pads
    tp_x, tp_col = 257.81, 262.89
    for ref, net, y, desc in (
        ("J3", "MOT_U", 92.71, "1.0 x 2.0 mm solder pad, motor U"),
        ("J4", "MOT_V", 97.79, "1.0 x 2.0 mm solder pad, motor V"),
        ("J5", "MOT_W", 102.87, "1.0 x 2.0 mm solder pad, motor W"),
    ):
        pad = f"{P}:CON-1P-1.0mmx2.0mm-Rectangular"
        sheet.component(pad, ref, "CON-1P-1.0mm*2.0mm-Rectangular", tp_x, y,
                        footprint="", description=desc)
        point = sheet.pin(pad, tp_x, y, 0, "1")
        wire(net, (point[0], point[1]), (tp_col, y))
        label(net, tp_col, y)

    # ------------------------------------------------------- test pads (stacked)
    # They live in the gap between MCU and MOTOR: the drawing sheet's own title
    # block owns x >= 108 / y >= 165, so nothing may be placed there.
    for index, (ref, net, desc) in enumerate(
        (
            ("TP4", "FORCE_P", "φ0.8 测试点，一维力传感器预留输入 P"),
            ("TP5", "FORCE_N", "φ0.8 测试点，一维力传感器预留输入 N"),
        )
    ):
        y = 107.95 + index * 5.08
        sheet.component("Connector:TestPoint", ref, "TP0.8", tp_x, y,
                        footprint="TestPoint:TestPoint_Pad_D1.0mm", description=desc,
                        value_visible=False)
        wire(net, (tp_x, y), (tp_col, y))
        label(net, tp_col, y)
    for index, net in enumerate(("VBUS", "PWR_3V3")):
        y = 118.11 + index * 5.08
        sheet.component("Connector:TestPoint", f"TP{6 + index}", "TP0.8", tp_x, y,
                        footprint="TestPoint:TestPoint_Pad_D1.0mm",
                        description=f"φ0.8 测试点，{net} 电源轨",
                        value_visible=False)
        wire(net, (tp_x, y), (tp_col, y))
        sheet.power(f"{P}:{net}", next_power(), tp_col, y)
    sheet.component("Connector:TestPoint", "TP8", "TP0.8", tp_x, 128.27,
                    footprint="TestPoint:TestPoint_Pad_D1.0mm",
                    description="φ0.8 测试点，NRST 复位网络",
                    value_visible=False)
    wire("NRST", (tp_x, 128.27), (tp_col, 128.27))
    label("NRST", tp_col, 128.27)
    sheet.text(
        "note:tp",
        "J3/J4/J5 = MOT_U/V/W 焊接盘（1.0×2.0mm Rectangular）；"
        "TP4/5 = FORCE_P/N；TP6 = VBUS 4.2~15V；TP7 = PWR_3V3 3.3V；TP8 = NRST",
        20.32,
        183.39,
        1.27,
    )

    # ------------------------------------------------------------ revision table
    table_l, table_t = 20.32, 186.69
    table_r, table_b = 107.95, 203.2
    header_y = 193.04
    sheet.rectangle("table:outer", table_l, table_t, table_r, table_b)
    sheet.rectangle("table:header", table_l, table_t, table_r, header_y)
    for index, x in enumerate((35.56, 58.42, 76.2)):
        sheet.rectangle(f"table:col{index}", x, table_t, x, table_b)
    for label, x in (("Rev", 21.59), ("Date", 36.83), ("Author", 59.69), ("Changes", 77.47)):
        sheet.text(f"table:h:{label}", label, x, 191.77, 1.27)
    sheet.text("table:rev", "V1.00", 21.59, 199.39, 1.27)
    sheet.text("table:date", "2026-10-11", 36.83, 199.39, 1.27)
    sheet.text("table:author", "Codex", 59.69, 199.39, 1.27)
    sheet.text("table:changes", "V1.12资源表/EN上拉/外置晶振", 77.47, 199.39, 1.27)

    sheet.text(
        "title",
        "LA150C RDIVER V1.00 - TOP\n层次页：POWER / MCU / MOTOR / ENCODER / COMMUNICATION",
        20.32,
        12.7,
        1.5,
    )
    sheet.text(
        "note:power",
        "电源流向：J2 PIN3 VBUS(4.2~15V, 12V 额定) → [D3 SMF16CA] → [SCT2230MLUAR 同步降压] → PWR_3V3 → [MP6543H V3P3 + 磁珠] → PWR_3V3A",
        20.32,
        15.24,
        1.27,
    )
    sheet.text(
        "note:iface",
        "整机对外接口：J2 4×Ø0.5mm 焊接孔（0.8mm 外径，2.54mm 间距）"
        " PIN1 CAN_L / PIN2 CAN_H / PIN3 12V / PIN4 GND；U/V/W 与 SWD 不引出到该连接器",
        20.32,
        17.78,
        1.27,
    )

    # --------------------------------------------------------------- audit
    def _collinear_overlap(a1, a2, b1, b2) -> bool:
        if abs(a1[0] - a2[0]) < 1e-6 and abs(b1[0] - b2[0]) < 1e-6:
            if abs(a1[0] - b1[0]) > 1e-6:
                return False
            lo = max(min(a1[1], a2[1]), min(b1[1], b2[1]))
            hi = min(max(a1[1], a2[1]), max(b1[1], b2[1]))
            return hi - lo > 1e-6
        if abs(a1[1] - a2[1]) < 1e-6 and abs(b1[1] - b2[1]) < 1e-6:
            if abs(a1[1] - b1[1]) > 1e-6:
                return False
            lo = max(min(a1[0], a2[0]), min(b1[0], b2[0]))
            hi = min(max(a1[0], a2[0]), max(b1[0], b2[0]))
            return hi - lo > 1e-6
        return False

    def _crosses(a1, a2, b1, b2) -> bool:
        a_vert = abs(a1[0] - a2[0]) < 1e-6
        b_vert = abs(b1[0] - b2[0]) < 1e-6
        if a_vert == b_vert:
            return False
        v1, v2, h1, h2 = (a1, a2, b1, b2) if a_vert else (b1, b2, a1, a2)
        vx, vy1, vy2 = v1[0], min(v1[1], v2[1]), max(v1[1], v2[1])
        hy, hx1, hx2 = h1[1], min(h1[0], h2[0]), max(h1[0], h2[0])
        return hx1 < vx < hx2 and vy1 < hy < vy2

    problems: list[str] = []
    crossings: list[tuple[str, str]] = []
    for index, (net_a, a1, a2) in enumerate(wires):
        for net_b, b1, b2 in wires[index + 1:]:
            if net_a == net_b:
                continue
            if _collinear_overlap(a1, a2, b1, b2):
                problems.append(f"{net_a} and {net_b} overlap on a shared wire")
            elif _crosses(a1, a2, b1, b2):
                crossings.append((net_a, net_b))
    if problems:
        raise ValueError("TOP audit failed:\n  " + "\n  ".join(problems))

    sheet.write()
    print(f"wrote {sheet.path}")
    print(f"wires: {len(wires)}, crossings: {len(crossings)}")
    for pair in crossings:
        print(f"  crossing: {pair[0]} x {pair[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
