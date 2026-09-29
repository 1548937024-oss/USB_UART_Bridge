#!/usr/bin/env python3
"""Assemble the MicroDriver V2.10 project symbol library.

The project keeps a single self-contained ``.kicad_sym`` so that schematic
data never references a user-private or installation path.  Symbols are pulled
from the classified LCSC libraries built earlier and from the KiCad standard
libraries; existing project symbols (power rails, PWR_FLAG) are preserved.

Later sources win on name collisions, so list the most specific library last.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET = PROJECT_ROOT / "library" / "MicroDriver_V2.10.kicad_sym"

CLASSIFIED_ROOT = Path(
    r"D:\办公相关\项目相关\三花\03-灵巧手项目\O-外置驱动器"
    r"\Library\Private\LCSC_Classified\libraries"
)
KICAD_SYMBOLS = Path(r"D:\KiCad10.0\share\kicad\symbols")

# KiCad standard symbols used directly by the V2.10 redraw.
STANDARD_SYMBOLS = [
    ("Device", "Device.kicad_sym", "R"),
    ("Device", "Device.kicad_sym", "C"),
    ("Device", "Device.kicad_sym", "L"),
    ("Device", "Device.kicad_sym", "LED"),
    ("Device", "Device.kicad_sym", "D_TVS"),
    ("Transistor_FET", "Transistor_FET.kicad_sym", "Q_PMOS_GSD"),
]


def collect_groups() -> list[tuple[str, dict[str, list[k.Node]]]]:
    groups: list[tuple[str, dict[str, list[k.Node]]]] = []

    if TARGET.is_file():
        groups.append(("project", k.read_library(TARGET)))

    for library in sorted(CLASSIFIED_ROOT.glob("*/*.kicad_sym")):
        groups.append((f"lcsc:{library.parent.name}", k.read_library(library)))

    standard: dict[str, list[k.Node]] = {}
    for _nickname, filename, name in STANDARD_SYMBOLS:
        library = k.read_library(KICAD_SYMBOLS / filename)
        if name not in library:
            raise SystemExit(f"{name} not found in {filename}")
        standard[name] = copy.deepcopy(library[name])
    groups.append(("kicad-standard", standard))

    return groups


# Two-terminal protection and passives that imported as "unspecified"; the
# electrical type should be passive so ERC does not flag them as connecting
# an undriven pin to a passive one.
PASSIVE_SYMBOLS = {
    "PESDNC2XD5VB",
    "PESD1CAN,215",
    "LBAV99WT1G",
    "SMBJ58CA",
    "BLM15AG601SN1D",
    "CSTNE8M00G52A000R0",
    "NCP15XH103F03RC",
    "TLV74333PDBVR",
}


def set_passive(node: k.Node) -> None:
    if not isinstance(node, list):
        return
    if node and node[0] == "pin" and len(node) > 1:
        node[1] = "passive"
    for item in node:
        if isinstance(item, list):
            set_passive(item)


def main() -> int:
    merged: dict[str, list[k.Node]] = {}
    origin: dict[str, str] = {}
    for label, symbols in collect_groups():
        for name, definition in symbols.items():
            definition = copy.deepcopy(definition)
            if name in PASSIVE_SYMBOLS:
                set_passive(definition)
            merged[name] = definition
            origin[name] = label

    root: list[k.Node] = [
        "kicad_symbol_lib",
        ["version", "20251024"],
        ["generator", k.quote("kicad_symbol_editor")],
        ["generator_version", k.quote("10.0")],
    ]
    for name in sorted(merged):
        definition = merged[name]
        definition[1] = k.quote(name)
        root.append(definition)

    TARGET.write_text(k.serialize(root) + "\n", encoding="utf-8", newline="\n")

    counts: dict[str, int] = {}
    for label in origin.values():
        counts[label] = counts.get(label, 0) + 1
    print(f"{TARGET.name}: {len(merged)} symbols")
    for label in sorted(counts):
        print(f"  {label}: {counts[label]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
