#!/usr/bin/env python3
"""Author the LA150C V1.00 custom symbols into the project library.

Every pin table below is taken from the device datasheet, not from a
reference design:

* GD32F503REL7  - GD32F503xx Datasheet Rev0.9RC6, Table 2-5 (LQFP-64);
* MP6543HGL     - MP6543H Rev1.0, "PIN FUNCTIONS" p4/p5 (QFN-24);
* MT6701        - Magntek MT6701 Rev1.5 pin table (QFN-16);
* TCAN3413DDFR  - TI TCAN3413/3414, Table 4-1 (SOT-23-8);
* SCT2230MLUAR  - Silicon Content SCT2230M Rev1.2, PIN FUNCTIONS (7L ECLGA);
* DF52-4P-0.8C  - Hirose DF52 series 4-pin, pin 1 VCC / 2 GND / 3 CANH / 4 CANL.

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
    number: str, name: str, kind: str, x: float, y: float, angle: float
) -> k.Node:
    return [
        "pin",
        kind,
        "line",
        ["at", k.number(x), k.number(y), k.number(angle)],
        ["length", k.number(PIN_LENGTH)],
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


def _mcu_left() -> list[tuple[str, str, str]]:
    return [
        ("14", "PA0/ADC2_IN0", "bidirectional"),
        ("15", "PA1", "bidirectional"),
        ("16", "PA2", "bidirectional"),
        ("17", "PA3/ADC1_IN3", "bidirectional"),
        ("20", "PA4", "bidirectional"),
        ("21", "PA5/SPI2_SCK", "bidirectional"),
        ("22", "PA6/SPI2_MISO", "bidirectional"),
        ("23", "PA7/ADC0_IN7", "bidirectional"),
        ("26", "PB0/ADC01_IN8", "bidirectional"),
        ("27", "PB1/ADC01_IN9", "bidirectional"),
        ("28", "PB2/BOOT1", "bidirectional"),
        ("58", "PB6/ADC1_IN9", "bidirectional"),
        ("59", "PB7/ADC1_IN8", "bidirectional"),
        ("29", "PB10/ADC1_IN16", "bidirectional"),
        ("30", "PB11/ADC2_IN16", "bidirectional"),
        ("33", "PB12/CAN0_RX", "bidirectional"),
        ("34", "PB13/CAN0_TX", "bidirectional"),
        ("35", "PB14", "bidirectional"),
        ("36", "PB15", "bidirectional"),
        ("8", "PC0/TIMER7_CH0_ON", "bidirectional"),
        ("9", "PC1/TIMER7_CH1_ON", "bidirectional"),
        ("10", "PC2/TIMER7_CH2_ON", "bidirectional"),
        ("11", "PC3", "bidirectional"),
        ("24", "PC4/ADC01_IN14", "bidirectional"),
    ]


def _mcu_right() -> list[tuple[str, str, str]]:
    return [
        ("25", "PC5/ADC01_IN15", "bidirectional"),
        ("37", "PC6/TIMER7_CH0", "bidirectional"),
        ("38", "PC7/TIMER7_CH1", "bidirectional"),
        ("39", "PC8/TIMER7_CH2", "bidirectional"),
        ("40", "PC9/TIMER7_CH3", "bidirectional"),
        ("51", "PC10", "bidirectional"),
        ("52", "PC11", "bidirectional"),
        ("53", "PC12", "bidirectional"),
        ("2", "PC13", "bidirectional"),
        ("3", "PC14-OSC32IN", "bidirectional"),
        ("4", "PC15-OSC32OUT", "bidirectional"),
        ("41", "PA8", "bidirectional"),
        ("42", "PA9", "bidirectional"),
        ("43", "PA10", "bidirectional"),
        ("44", "PA11/TIMER7_CH0", "bidirectional"),
        ("45", "PA12/TIMER7_CH1", "bidirectional"),
        ("46", "PA13/SWDIO", "bidirectional"),
        ("49", "PA14/SWCLK", "bidirectional"),
        ("50", "PA15", "bidirectional"),
        ("55", "PB3", "bidirectional"),
        ("56", "PB4", "bidirectional"),
        ("57", "PB5", "bidirectional"),
        ("61", "PB8", "bidirectional"),
        ("62", "PB9", "bidirectional"),
    ]


SPECS: dict[str, dict] = {
    # GD32F503REL7, LQFP-64, pins grouped by function (power / analog /
    # PWM / communication / debug) rather than by package order.
    "GD32F503REL7": dict(
        ref="U",
        value="GD32F503REL7",
        mpn="GD32F503REL7",
        lcsc="C54318468",
        manufacturer="GigaDevice",
        description="GD32F503REL7 Cortex-M4F MCU, LQFP-64, 512KB flash",
        width=48.26,
        height=66.04,
        left=_mcu_left(),
        right=_mcu_right(),
        top=[
            ("1", "VBAT", "power_in"),
            ("19", "VDD", "power_in"),
            ("32", "VDD", "power_in"),
            ("48", "VDD", "power_in"),
            ("64", "VDD", "power_in"),
            ("13", "VDDA/VREFP", "power_in"),
        ],
        bottom=[
            ("18", "VSS", "power_in"),
            ("31", "VSS", "power_in"),
            ("47", "VSS", "power_in"),
            ("63", "VSS", "power_in"),
            ("12", "VSSA/VREFN", "power_in"),
            ("7", "NRST", "bidirectional"),
            ("60", "BOOT0", "input"),
            ("5", "OSCIN/PD0", "bidirectional"),
            ("6", "OSCOUT/PD1", "bidirectional"),
            ("54", "PD2", "bidirectional"),
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
    # MT6701 magnetic angle sensor, QFN-16 + EP.
    "MT6701": dict(
        ref="U",
        value="MT6701",
        mpn="MT6701QT-ACD",
        lcsc="C49257133",
        manufacturer="Magntek",
        description="14-bit magnetic angle sensor, SSI/ABZ/I2C, QFN-16",
        width=20.32,
        height=22.86,
        left=[
            ("5", "PUSH", "output"),
            ("6", "A/DO", "bidirectional"),
            ("7", "B/CLK", "bidirectional"),
            ("8", "Z/CSN", "bidirectional"),
            ("1", "NC1", "no_connect"),
            ("2", "NC2", "no_connect"),
            ("3", "NC3", "no_connect"),
            ("4", "NC4", "no_connect"),
        ],
        right=[
            ("13", "VDD", "power_in"),
            ("14", "MODE", "input"),
            ("15", "OUT", "output"),
            ("9", "U", "bidirectional"),
            ("10", "NC5", "no_connect"),
            ("11", "V", "bidirectional"),
            ("12", "W", "bidirectional"),
            ("16", "GND", "power_in"),
        ],
        bottom=[("17", "EP", "passive")],
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
    # Hirose DF52 4-pin 0.8 mm wire-to-board connector.
    "DF52-4P-0.8C": dict(
        ref="J",
        value="DF52-4P-0.8C",
        mpn="DF52-4P-0.8C",
        manufacturer="Hirose",
        description="DF52 0.8mm 4pin connector, VCC/GND/CANH/CANL",
        width=10.16,
        height=12.7,
        left=[
            ("1", "VCC", "passive"),
            ("2", "GND", "passive"),
            ("3", "CANH", "passive"),
            ("4", "CANL", "passive"),
        ],
    ),
    # 1x5 1.27 mm SWD header.
    "SWD-1X5-1.27": dict(
        ref="J",
        value="SWD-1X5-1.27",
        mpn="SWD-1X5-1.27",
        description="1x5 1.27mm SWD debug header",
        width=10.16,
        height=15.24,
        left=[
            ("1", "PWR_3V3", "passive"),
            ("2", "SWDIO", "passive"),
            ("3", "SWCLK", "passive"),
            ("4", "GND", "passive"),
            ("5", "NRST", "passive"),
        ],
    ),
    # 8 MHz three-terminal ceramic resonator (BOM gap doc lists
    # CSTCE8M00G52-R0; hw design §3.2.2 asks for +/-10 ppm, which the
    # resonator cannot meet - recorded as an open item).
    "CSTCE8M00G52-R0": dict(
        ref="X",
        value="CSTCE8M00G52-R0",
        mpn="CSTCE8M00G52-R0",
        manufacturer="Murata",
        description="8MHz three-terminal ceramic resonator, SMD-3225",
        width=10.16,
        height=7.62,
        left=[("1", "XI", "passive")],
        right=[("3", "XO", "passive")],
        bottom=[("2", "GND", "power_in")],
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
        root.append(build_symbol(name, spec))
        added.append(name)
    TARGET.write_text(k.serialize(root) + "\n", encoding="utf-8", newline="\n")
    print(f"added {len(added)} symbols: {', '.join(added)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
