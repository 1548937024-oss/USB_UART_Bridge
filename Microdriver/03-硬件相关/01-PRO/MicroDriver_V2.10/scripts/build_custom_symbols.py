#!/usr/bin/env python3
"""Author the MicroDriver V2.10 custom symbols into the project library.

Pin tables come from the device datasheets:

* MPM3572      - MPM3572_r0.8_Sanhua.pdf, "PIN FUNCTIONS", page 4
* TPT481L1-DF6R- 3PEAK TPT481 datasheet (LCSC C20198121), page 4
* SMBJ58CA     - 2-terminal bidirectional TVS, DO-214AA
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET = PROJECT_ROOT / "library" / "MicroDriver_V2.10.kicad_sym"

PIN_LENGTH = 3.81
PIN_PITCH = 2.54
FONT = ["font", ["size", "1.27", "1.27"]]


def pin_node(number: str, name: str, kind: str, x: float, y: float, angle: float) -> k.Node:
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
    hidden = spec.get("hidden", [])

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
    # spread the hidden no-connect pins instead of stacking them on one point,
    # so each can carry its own no-connect marker and the geometry audit can
    # tell them apart
    for index, (number, label) in enumerate(hidden):
        y = round(top - (len(right) + index) * PIN_PITCH, 4)
        pins.append(pin_node(number, label, "no_connect", width / 2 + PIN_LENGTH, y, 180))

    body = [
        "symbol",
        k.quote(f"{name}_0_1"),
        body_node(width, height),
    ]
    unit = [
        "symbol",
        k.quote(f"{name}_1_0"),
        *pins,
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
        ["property", k.quote("Reference"), k.quote(spec.get("ref", "U")),
         ["at", "0", "0", "0"], ["show_name", "no"], ["do_not_autoplace", "no"],
         ["effects", FONT]],
        ["property", k.quote("Value"), k.quote(spec.get("value", name)),
         ["at", "0", "0", "0"], ["show_name", "no"], ["do_not_autoplace", "no"],
         ["effects", FONT]],
        ["property", k.quote("Footprint"), k.quote(spec.get("footprint", "")),
         ["at", "0", "0", "0"], ["hide", "yes"], ["show_name", "no"], ["do_not_autoplace", "no"],
         ["effects", FONT]],
        ["property", k.quote("Datasheet"), k.quote(spec.get("datasheet", "")),
         ["at", "0", "0", "0"], ["hide", "yes"], ["show_name", "no"], ["do_not_autoplace", "no"],
         ["effects", FONT]],
        ["property", k.quote("Description"), k.quote(spec.get("description", "")),
         ["at", "0", "0", "0"], ["hide", "yes"], ["show_name", "no"], ["do_not_autoplace", "no"],
         ["effects", FONT]],
        body,
        unit,
        ["embedded_fonts", "no"],
    ]


SPECS: dict[str, dict] = {
    # 24-pin LGA 6x6 power module, 10V-80V input, 0.6A.
    "MPM3572": dict(
        value="MPM3572",
        footprint="",
        description="80V/0.6A buck power module LGA-24(6x6)",
        width=25.4,
        height=30.48,
        left=[
            ("23", "VIN", "power_in"),
            ("24", "VIN", "power_in"),
            ("1", "EN", "input"),
            ("6", "FREQ", "input"),
            ("4", "FB", "input"),
        ],
        right=[
            ("7", "OUT", "passive"),
            ("8", "OUT", "passive"),
            ("15", "SW", "passive"),
            ("16", "SW", "passive"),
            ("17", "BST", "passive"),
            ("3", "VCC", "passive"),
        ],
        bottom=[
            ("9", "GND", "power_in"),
            ("10", "GND", "power_in"),
            ("11", "GND", "power_in"),
            ("12", "GND", "power_in"),
            ("20", "GND", "power_in"),
            ("21", "GND", "power_in"),
            ("22", "GND", "power_in"),
            ("5", "AGND", "power_in"),
        ],
        hidden=[("2", "NC"), ("13", "TP1"), ("14", "NC"), ("18", "TP2"), ("19", "NC")],
    ),
    # RS485 half-duplex transceiver, DFN-8L 3x3 plus exposed pad.
    "TPT481L1-DF6R": dict(
        value="TPT481L1-DF6R",
        description="RS485/RS422 transceiver DFN-8L(3x3)",
        width=17.78,
        height=15.24,
        left=[("1", "R", "output"), ("2", "~{RE}", "input"), ("3", "DE", "input"), ("4", "D", "input")],
        right=[("8", "VCC", "power_in"), ("7", "B", "bidirectional"), ("6", "A", "bidirectional"), ("5", "GND", "power_in")],
        bottom=[("9", "PE", "passive")],
    ),
    # Bidirectional TVS, SMB (DO-214AA).
    "SMBJ58CA": dict(
        ref="D",
        value="SMBJ58CA",
        description="Bidirectional TVS 58V standoff 600W SMB",
        width=7.62,
        height=7.62,
        left=[("1", "A1", "passive")],
        right=[("2", "A2", "passive")],
    ),
    # CAN FD transceiver, TSOT-23-8.  Pin order taken from the V2.10 sheet
    # (1 TXD / 2 GND / 3 VCC / 4 RXD / 5 VIO / 6 CANL / 7 CANH / 8 STB).
    "TCAN3413DDFR": dict(
        value="TCAN3413DDFR",
        description="CAN FD 收发器 3~3.6V TSOT-23-8",
        width=17.78,
        height=15.24,
        left=[
            ("1", "TXD", "input"),
            ("2", "GND", "passive"),
            ("3", "VCC", "passive"),
            ("4", "RXD", "output"),
        ],
        right=[
            ("8", "STB", "input"),
            ("7", "CANH", "bidirectional"),
            ("6", "CANL", "bidirectional"),
            ("5", "VIO", "passive"),
        ],
    ),
    # GD32F503REL7, BGA-64.  Pin numbers are the datasheet ball names
    # (Table 2-7, GD32F503xx Datasheet Rev0.9RC6) so the symbol matches the
    # package 1:1; pin names carry the signal function.
    "GD32F503REL7": dict(
        ref="U",
        value="GD32F503REL7",
        description="GD32F503REL7 Cortex-M33 MCU, BGA-64, 512KB flash",
        width=30.48,
        height=63.5,
        left=[
            ("H5", "PA0", "bidirectional"), ("E3", "PA1", "bidirectional"),
            ("F3", "PA2", "bidirectional"), ("H2", "PA3", "bidirectional"),
            ("D4", "PA4", "bidirectional"), ("E4", "PA5", "bidirectional"),
            ("G3", "PA6", "bidirectional"), ("H3", "PA7", "bidirectional"),
            ("E6", "PA8", "bidirectional"), ("D7", "PA9", "bidirectional"),
            ("D6", "PA10", "bidirectional"), ("C8", "PA11", "bidirectional"),
            ("B8", "PA12", "bidirectional"), ("C7", "PA13", "bidirectional"),
            ("C6", "PA14", "bidirectional"), ("A7", "PA15", "bidirectional"),
            ("E2", "PC0", "bidirectional"), ("C3", "PC1", "bidirectional"),
            ("D3", "PC2", "bidirectional"), ("G4", "PC3", "bidirectional"),
            ("D5", "PC4", "bidirectional"), ("F4", "PC5", "bidirectional"),
            ("E8", "PC6", "bidirectional"), ("E7", "PC7", "bidirectional"),
        ],
        right=[
            ("E5", "PB0", "bidirectional"), ("F5", "PB1", "bidirectional"),
            ("H4", "PB2/BOOT1", "bidirectional"), ("A5", "PB3", "bidirectional"),
            ("C4", "PB4", "bidirectional"), ("B4", "PB5", "bidirectional"),
            ("A4", "PB6", "bidirectional"), ("A3", "PB7", "bidirectional"),
            ("G5", "PB8", "bidirectional"), ("A2", "PB9", "bidirectional"),
            ("H6", "PB10", "bidirectional"), ("H7", "PB11", "bidirectional"),
            ("G8", "PB12", "bidirectional"), ("G6", "PB13", "bidirectional"),
            ("F8", "PB14", "bidirectional"), ("F7", "PB15", "bidirectional"),
            ("F6", "PC8", "bidirectional"), ("D8", "PC9", "bidirectional"),
            ("C5", "PC10", "bidirectional"), ("B6", "PC11", "bidirectional"),
            ("A6", "PC12", "bidirectional"), ("B1", "PC13", "bidirectional"),
            ("C1", "PC14-OSC32IN", "bidirectional"),
            ("D1", "PC15-OSC32OUT", "bidirectional"),
        ],
        top=[
            ("A1", "VDD", "power_in"), ("A8", "VDD", "power_in"),
            ("H1", "VDD", "power_in"), ("H8", "VDD", "power_in"),
            ("C2", "VBAT", "power_in"), ("G1", "VDDA/VREFP", "power_in"),
        ],
        bottom=[
            ("B2", "VSS", "power_in"), ("B7", "VSS", "power_in"),
            ("G2", "VSS", "power_in"), ("G7", "VSS", "power_in"),
            ("F2", "VSSA/VREFN", "power_in"), ("E1", "OSCIN-PD0", "bidirectional"),
            ("F1", "OSCOUT-PD1", "bidirectional"), ("B5", "PD2", "bidirectional"),
            ("D2", "NRST", "input"), ("B3", "BOOT0", "input"),
        ],
    ),
}


def main() -> int:
    root = k.Parser(TARGET.read_text(encoding="utf-8")).parse()
    existing = {
        k.atom(item[1])
        for item in root[1:]
        if isinstance(item, list) and item and item[0] == "symbol"
    }

    added = []
    for name, spec in SPECS.items():
        # always regenerate: the pin table is the source of truth, so a spec
        # change must overwrite a previously emitted symbol
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
    print(f"added {len(added)} symbols: {', '.join(added) if added else '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
