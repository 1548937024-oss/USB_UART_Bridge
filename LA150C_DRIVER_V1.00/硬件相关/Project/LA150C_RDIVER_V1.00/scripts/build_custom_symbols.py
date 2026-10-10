#!/usr/bin/env python3
"""Author the LA150C V1.00 custom symbols into the project library.

Every pin table below is taken from the device datasheet, not from a
reference design:

* GD32F503REL7  - GD32F503xx Datasheet Rev0.9RC6, Table 2-5 (BGA-64);
* MP6543HGL     - MP6543H Rev1.0, "PIN FUNCTIONS" p4/p5 (QFN-24);
* TCAN3413DDFR  - TI TCAN3413/3414, Table 4-1 (SOT-23-8);
* SCT2230MLUAR  - Silicon Content SCT2230M Rev1.2, PIN FUNCTIONS (7L ECLGA);

Pin numbers are the package numbers so the symbol can be checked against the
datasheet one-to-one; pin names carry the signal function.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET = PROJECT_ROOT / "library" / "LA150C_RDIVER_V1.00.kicad_sym"

PIN_LENGTH = 3.81
PIN_PITCH = 2.54
FONT = ["font", ["size", "1.27", "1.27"]]


def pin_node(
    number: str,
    name: str,
    kind: str,
    x: float,
    y: float,
    angle: float,
    length: float = PIN_LENGTH,
) -> k.Node:
    return [
        "pin",
        kind,
        "line",
        ["at", k.number(x), k.number(y), k.number(angle)],
        ["length", k.number(length)],
        ["name", k.quote(name), ["effects", FONT]],
        ["number", k.quote(number), ["effects", FONT]],
    ]


def body_node(width: float, height: float) -> k.Node:
    return [
        "rectangle",
        ["start", k.number(-width / 2), k.number(height / 2)],
        ["end", k.number(width / 2), k.number(-height / 2)],
        ["stroke", ["width", "0.254"], ["type", "default"]],
        ["fill", ["type", "background"]],
    ]


def build_symbol(name: str, spec: dict) -> list[k.Node]:
    width = spec["width"]
    height = spec["height"]
    left = spec.get("left", [])
    right = spec.get("right", [])
    top_pins = spec.get("top", [])
    bottom = spec.get("bottom", [])

    rows = max(len(left), len(right), 1)
    top = (rows - 1) * PIN_PITCH / 2

    pins: list[k.Node] = []
    for index, (number, label, kind) in enumerate(left):
        y = round(top - index * PIN_PITCH, 4)
        pins.append(pin_node(number, label, kind, -width / 2 - PIN_LENGTH, y, 0))
    for index, (number, label, kind) in enumerate(right):
        y = round(top - index * PIN_PITCH, 4)
        pins.append(pin_node(number, label, kind, width / 2 + PIN_LENGTH, y, 180))
    if top_pins:
        span = (len(top_pins) - 1) * PIN_PITCH / 2
        for index, (number, label, kind) in enumerate(top_pins):
            x = round(-span + index * PIN_PITCH, 4)
            pins.append(pin_node(number, label, kind, x, height / 2 + PIN_LENGTH, 270))
    if bottom:
        span = (len(bottom) - 1) * PIN_PITCH / 2
        for index, (number, label, kind) in enumerate(bottom):
            x = round(-span + index * PIN_PITCH, 4)
            pins.append(pin_node(number, label, kind, x, -height / 2 - PIN_LENGTH, 90))

    body = ["symbol", k.quote(f"{name}_0_1"), body_node(width, height)]
    unit = ["symbol", k.quote(f"{name}_1_0"), *pins]

    return [
        "symbol",
        k.quote(name),
        ["pin_names", ["offset", "0.762"]],
        ["exclude_from_sim", "no"],
        ["in_bom", "yes"],
        ["on_board", "yes"],
        ["in_pos_files", "yes"],
        ["duplicate_pin_numbers_are_jumpers", "no"],
        ["property", k.quote("Reference"), k.quote(spec.get("ref", "U")),
         ["at", "0", "0", "0"], ["show_name", "no"], ["do_not_autoplace", "no"],
         ["effects", FONT]],
        ["property", k.quote("Value"), k.quote(spec.get("value", name)),
         ["at", "0", "0", "0"], ["show_name", "no"], ["do_not_autoplace", "no"],
         ["effects", FONT]],
        ["property", k.quote("Footprint"), k.quote(spec.get("footprint", "")),
         ["at", "0", "0", "0"], ["hide", "yes"], ["show_name", "no"],
         ["do_not_autoplace", "no"], ["effects", FONT]],
        ["property", k.quote("Datasheet"), k.quote(spec.get("datasheet", "")),
         ["at", "0", "0", "0"], ["hide", "yes"], ["show_name", "no"],
         ["do_not_autoplace", "no"], ["effects", FONT]],
        ["property", k.quote("Description"), k.quote(spec.get("description", "")),
         ["at", "0", "0", "0"], ["hide", "yes"], ["show_name", "no"],
         ["do_not_autoplace", "no"], ["effects", FONT]],
        ["property", k.quote("MPN"), k.quote(spec.get("mpn", name)),
         ["at", "0", "0", "0"], ["hide", "yes"], ["show_name", "no"],
         ["do_not_autoplace", "no"], ["effects", FONT]],
        ["property", k.quote("LCSC Part"), k.quote(spec.get("lcsc", "")),
         ["at", "0", "0", "0"], ["hide", "yes"], ["show_name", "no"],
         ["do_not_autoplace", "no"], ["effects", FONT]],
        ["property", k.quote("Manufacturer"), k.quote(spec.get("manufacturer", "")),
         ["at", "0", "0", "0"], ["hide", "yes"], ["show_name", "no"],
         ["do_not_autoplace", "no"], ["effects", FONT]],
        body,
        unit,
        ["embedded_fonts", "no"],
    ]


def build_rectangular_solder_pad(name: str, spec: dict) -> list[k.Node]:
    """Build a one-pin solder-pad symbol with its connection point at origin."""
    body = [
        "symbol",
        k.quote(f"{name}_0_1"),
        [
            "rectangle",
            ["start", "-1.635", "-1"],
            ["end", "-0.635", "1"],
            ["stroke", ["width", "0.254"], ["type", "default"]],
            ["fill", ["type", "background"]],
        ],
    ]
    unit = [
        "symbol",
        k.quote(f"{name}_1_0"),
        pin_node("1", "PAD", "passive", 0, 0, 180, length=0.635),
    ]

    return [
        "symbol",
        k.quote(name),
        ["pin_names", ["offset", "0.762"]],
        ["exclude_from_sim", "no"],
        ["in_bom", "yes"],
        ["on_board", "yes"],
        ["in_pos_files", "yes"],
        ["duplicate_pin_numbers_are_jumpers", "no"],
        ["property", k.quote("Reference"), k.quote(spec.get("ref", "J")),
         ["at", "0", "0", "0"], ["show_name", "no"], ["do_not_autoplace", "no"],
         ["effects", FONT]],
        ["property", k.quote("Value"), k.quote(spec.get("value", name)),
         ["at", "0", "0", "0"], ["show_name", "no"], ["do_not_autoplace", "no"],
         ["effects", FONT]],
        ["property", k.quote("Footprint"), k.quote(spec.get("footprint", "")),
         ["at", "0", "0", "0"], ["hide", "yes"], ["show_name", "no"],
         ["do_not_autoplace", "no"], ["effects", FONT]],
        ["property", k.quote("Datasheet"), k.quote(spec.get("datasheet", "")),
         ["at", "0", "0", "0"], ["hide", "yes"], ["show_name", "no"],
         ["do_not_autoplace", "no"], ["effects", FONT]],
        ["property", k.quote("Description"), k.quote(spec.get("description", "")),
         ["at", "0", "0", "0"], ["hide", "yes"], ["show_name", "no"],
         ["do_not_autoplace", "no"], ["effects", FONT]],
        ["property", k.quote("MPN"), k.quote(spec.get("mpn", name)),
         ["at", "0", "0", "0"], ["hide", "yes"], ["show_name", "no"],
         ["do_not_autoplace", "no"], ["effects", FONT]],
        ["property", k.quote("LCSC Part"), k.quote(spec.get("lcsc", "")),
         ["at", "0", "0", "0"], ["hide", "yes"], ["show_name", "no"],
         ["do_not_autoplace", "no"], ["effects", FONT]],
        ["property", k.quote("Manufacturer"), k.quote(spec.get("manufacturer", "")),
         ["at", "0", "0", "0"], ["hide", "yes"], ["show_name", "no"],
         ["do_not_autoplace", "no"], ["effects", FONT]],
        body,
        unit,
        ["embedded_fonts", "no"],
    ]


def _mcu_left() -> list[tuple[str, str, str]]:
    return [
        ("H5", "PA0/ADC2_IN0", "bidirectional"),
        ("E3", "PA1", "bidirectional"),
        ("F3", "PA2", "bidirectional"),
        ("H2", "PA3/ADC1_IN3", "bidirectional"),
        ("D4", "PA4", "bidirectional"),
        ("E4", "PA5", "bidirectional"),
        ("G3", "PA6", "bidirectional"),
        ("H3", "PA7/ADC0_IN7", "bidirectional"),
        ("E5", "PB0/ADC01_IN8", "bidirectional"),
        ("F5", "PB1/ADC01_IN9", "bidirectional"),
        ("H4", "PB2/BOOT1", "bidirectional"),
        ("A4", "PB6/ADC1_IN9", "bidirectional"),
        ("A3", "PB7/ADC1_IN8", "bidirectional"),
        ("H6", "PB10/ADC1_IN16", "bidirectional"),
        ("H7", "PB11/ADC2_IN16", "bidirectional"),
        ("G8", "PB12/CANFD_RX", "bidirectional"),
        ("G6", "PB13/CANFD_TX", "bidirectional"),
        ("F8", "PB14", "bidirectional"),
        ("F7", "PB15", "bidirectional"),
        ("E2", "PC0/TIMER7_CH0_ON", "bidirectional"),
        ("C3", "PC1/TIMER7_CH1_ON", "bidirectional"),
        ("D3", "PC2/TIMER7_CH2_ON", "bidirectional"),
        ("G4", "PC3", "bidirectional"),
        ("D5", "PC4/ADC01_IN14", "bidirectional"),
    ]


def _mcu_right() -> list[tuple[str, str, str]]:
    return [
        ("F4", "PC5/ADC01_IN15", "bidirectional"),
        ("E8", "PC6/TIMER7_CH0", "bidirectional"),
        ("E7", "PC7/TIMER7_CH1", "bidirectional"),
        ("F6", "PC8/TIMER7_CH2", "bidirectional"),
        ("D8", "PC9/TIMER7_CH3", "bidirectional"),
        ("C5", "PC10", "bidirectional"),
        ("B6", "PC11", "bidirectional"),
        ("A6", "PC12", "bidirectional"),
        ("B1", "PC13", "bidirectional"),
        ("C1", "PC14-OSC32IN", "bidirectional"),
        ("D1", "PC15-OSC32OUT", "bidirectional"),
        ("E6", "PA8", "bidirectional"),
        ("D7", "PA9", "bidirectional"),
        ("D6", "PA10", "bidirectional"),
        ("C8", "PA11/TIMER7_CH0", "bidirectional"),
        ("B8", "PA12/TIMER7_CH1", "bidirectional"),
        ("C7", "PA13/SWDIO", "bidirectional"),
        ("C6", "PA14/SWCLK", "bidirectional"),
        ("A7", "PA15", "bidirectional"),
        ("A5", "PB3", "bidirectional"),
        ("C4", "PB4", "bidirectional"),
        ("B4", "PB5", "bidirectional"),
        ("G5", "PB8", "bidirectional"),
        ("A2", "PB9", "bidirectional"),
    ]


SPECS: dict[str, dict] = {
    # GD32F503REL7, BGA-64, pins grouped by function (power / analog /
    # PWM / communication / debug) rather than by package order.
    "GD32F503REL7": dict(
        ref="U",
        value="GD32F503REL7",
        mpn="GD32F503REL7",
        lcsc="C54318468",
        manufacturer="GigaDevice",
        footprint="Embedded Processors & Controllers:ucBGA-64_4x4mm_Layout8x8_P0.4mm",
        description="GD32F503REL7 Cortex-M33 MCU, BGA-64, 512KB flash",
        width=48.26,
        height=66.04,
        left=_mcu_left(),
        right=_mcu_right(),
        top=[
            ("C2", "VBAT", "power_in"),
            ("A1", "VDD", "power_in"),
            ("A8", "VDD", "power_in"),
            ("H1", "VDD", "power_in"),
            ("H8", "VDD", "power_in"),
            ("G1", "VDDA/VREFP", "power_in"),
        ],
        bottom=[
            ("B2", "VSS", "power_in"),
            ("B7", "VSS", "power_in"),
            ("G2", "VSS", "power_in"),
            ("G7", "VSS", "power_in"),
            ("F2", "VSSA/VREFN", "power_in"),
            ("D2", "NRST", "bidirectional"),
            ("B3", "BOOT0", "input"),
            ("E1", "OSCIN/PD0", "bidirectional"),
            ("F1", "OSCOUT/PD1", "bidirectional"),
            ("B5", "PD2", "bidirectional"),
        ],
    ),
    # MP6543HGL-Z, QFN-24 3x4 mm with exposed pad.
    "MP6543HGL-Z": dict(
        ref="U",
        value="MP6543HGL-Z",
        mpn="MP6543HGL-Z",
        lcsc="C3681371",
        manufacturer="MPS",
        description="22V/2A three-phase power stage, QFN-24 + EP",
        width=25.4,
        height=22.86,
        left=[
            ("1", "ENA", "input"),
            ("2", "ENB", "input"),
            ("3", "ENC", "input"),
            ("4", "PWMA", "input"),
            ("5", "PWMB", "input"),
            ("6", "PWMC", "input"),
            ("17", "OC_ADJ", "input"),
            ("24", "nSLEEP", "input"),
        ],
        right=[
            ("23", "SOA", "output"),
            ("22", "SOB", "output"),
            ("21", "SOC", "output"),
            ("20", "nFAULT", "open_collector"),
            ("18", "V3P3", "power_out"),
            ("14", "VCP", "passive"),
            ("19", "N/C", "no_connect"),
        ],
        top=[
            ("7", "VIN", "power_in"),
            ("13", "VIN", "power_in"),
            ("16", "VIN_LDO", "power_in"),
        ],
        bottom=[
            ("9", "SA", "passive"),
            ("10", "SB", "passive"),
            ("11", "SC", "passive"),
            ("8", "LSS", "power_in"),
            ("12", "LSS", "power_in"),
            ("15", "GND", "power_in"),
            ("25", "EP", "passive"),
        ],
    ),
    # TCAN3413DDFR, SOT-23-8.
    "TCAN3413DDFR": dict(
        ref="U",
        value="TCAN3413DDFR",
        mpn="TCAN3413DDFR",
        lcsc="C30111221",
        manufacturer="TI",
        description="CAN FD transceiver, 3.3V, 40 Mbps, SOT-23-8",
        width=17.78,
        height=12.7,
        left=[
            ("1", "TXD", "input"),
            ("4", "RXD", "output"),
        ],
        right=[
            ("7", "CANH", "bidirectional"),
            ("6", "CANL", "bidirectional"),
        ],
        top=[("3", "VCC", "power_in"), ("5", "VIO", "power_in")],
        bottom=[("2", "GND", "power_in"), ("8", "STB", "input")],
    ),
    # SCT2230MLUAR, 7L ECLGA 2.5x1.7 mm synchronous buck module.
    "SCT2230MLUAR": dict(
        ref="U",
        value="SCT2230MLUAR",
        mpn="SCT2230MLUAR",
        lcsc="C50199203",
        manufacturer="Silicon Content",
        description="17V/2A synchronous buck module with integrated inductor, 7L ECLGA",
        width=17.78,
        height=12.7,
        left=[
            ("6", "VIN", "power_in"),
            ("3", "EN", "input"),
            ("4", "BST", "passive"),
        ],
        right=[
            ("1", "VOUT", "power_out"),
            ("2", "FB", "input"),
            ("5", "SW", "passive"),
            ("7", "PGND", "power_in"),
        ],
    ),
    # QS01-compatible 1x3 1.0 mm SWD header: SWDIO / SWCLK / GND.
    "SWD-1X3-1.0": dict(
        ref="J",
        value="SWD-1X3-1.0",
        mpn="SWD-1X3-1.0",
        footprint="Connector_PinHeader_1.00mm:PinHeader_1x03_P1.00mm_Vertical",
        description="QS01-compatible 1x3 1.0mm SWD header, 1 SWDIO / 2 GND / 3 SWCLK",
        width=10.16,
        height=10.16,
        left=[
            ("1", "SWDIO", "passive"),
            ("2", "GND", "passive"),
            ("3", "SWCLK", "passive"),
        ],
    ),
    # Four solder holes for the external CAN/power harness.
    "SOLDER_HOLES_4P_0.5MM": dict(
        ref="J",
        value="SOLDER_HOLES_4P_0.5MM",
        mpn="SOLDER_HOLES_4P_0.5MM",
        footprint="LA150C_RDIVER_V1.00:Solder_Holes_4P_0.5mm",
        description="4x solder holes, 0.5mm drill, 0.8mm pad, 2.54mm pitch",
        width=10.16,
        height=12.7,
        left=[
            ("1", "CAN_L", "passive"),
            ("2", "CAN_H", "passive"),
            ("3", "VBUS", "passive"),
            ("4", "GND", "passive"),
        ],
    ),
    # Single rectangular solder pad for the motor power wires.
    "CON-1P-1.0mmx2.0mm-Rectangular": dict(
        builder="rectangular_pad",
        ref="J",
        value="CON-1P-1.0mm*2.0mm-Rectangular",
        mpn="CON-1P-1.0mm*2.0mm-Rectangular",
        footprint="LA150C_RDIVER_V1.00:CON-1P-1.0mmx2.0mm-Rectangular",
        description="One rectangular SMD solder pad, 1.0 mm x 2.0 mm",
    ),
}


def main() -> int:
    root = k.Parser(TARGET.read_text(encoding="utf-8")).parse()
    added = []
    for name, spec in SPECS.items():
        root[1:] = [
            item
            for item in root[1:]
            if not (
                isinstance(item, list)
                and item
                and item[0] == "symbol"
                and k.atom(item[1]) == name
            )
        ]
        if spec.get("builder") == "rectangular_pad":
            root.append(build_rectangular_solder_pad(name, spec))
        else:
            root.append(build_symbol(name, spec))
        added.append(name)
    TARGET.write_text(k.serialize(root) + "\n", encoding="utf-8", newline="\n")
    print(f"added {len(added)} symbols: {', '.join(added)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
