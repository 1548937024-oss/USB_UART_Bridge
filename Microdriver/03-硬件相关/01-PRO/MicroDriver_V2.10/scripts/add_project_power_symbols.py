#!/usr/bin/env python3
"""Add the MicroDriver V2.10 power symbols to the project symbol library.

``VBUS_IN_BAR`` is derived from the existing ``VBUS_BAR`` symbol so that the
drawing style stays consistent.  ``PWR_FLAG`` is taken verbatim from the
KiCad 10 ``power`` library, which already draws the visible flag outline
required by the project rules.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET = PROJECT_ROOT / "library" / "PowerSymbols.kicad_sym"
KICAD_POWER_LIB = Path(r"D:\KiCad10.0\share\kicad\symbols\power.kicad_sym")


def find_symbol(root: list[k.Node], name: str) -> list[k.Node] | None:
    for item in root[1:]:
        if isinstance(item, list) and item and item[0] == "symbol":
            if k.atom(item[1]) == name:
                return item
    return None


def rename_symbol(node: list[k.Node], old: str, new: str) -> None:
    node[1] = k.quote(new)
    for item in node[1:]:
        if isinstance(item, list) and item and item[0] == "symbol":
            child = k.atom(item[1])
            if child.startswith(old):
                item[1] = k.quote(new + child[len(old) :])


def set_property(node: list[k.Node], name: str, value: str) -> None:
    for property_node in k.direct_all(node, "property"):
        if len(property_node) >= 3 and k.atom(property_node[1]) == name:
            property_node[2] = k.quote(value)
            return
    raise KeyError(f"Property {name!r} not found")


def rename_power_pin(node: k.Node, name: str) -> None:
    if not isinstance(node, list):
        return
    if node and node[0] == "pin":
        name_node = k.direct(node, "name")
        if name_node is not None and len(name_node) >= 2:
            name_node[1] = k.quote(name)
    for item in node:
        if isinstance(item, list):
            rename_power_pin(item, name)


def main() -> int:
    root = k.Parser(TARGET.read_text(encoding="utf-8")).parse()
    existing = {
        k.atom(item[1])
        for item in root[1:]
        if isinstance(item, list) and item and item[0] == "symbol"
    }

    if "VBUS_IN_BAR" not in existing:
        source = find_symbol(root, "VBUS_BAR")
        if source is None:
            raise SystemExit("VBUS_BAR not found; cannot derive VBUS_IN_BAR")
        symbol = copy.deepcopy(source)
        rename_symbol(symbol, "VBUS_BAR", "VBUS_IN_BAR")
        set_property(symbol, "Value", "VBUS_IN")
        set_property(
            symbol,
            "Description",
            "电源符号创建名为 'VBUS_IN' 的全局标签",
        )
        rename_power_pin(symbol, "VBUS_IN")
        root.append(symbol)

    if "PWR_FLAG" not in existing:
        standard = k.Parser(KICAD_POWER_LIB.read_text(encoding="utf-8")).parse()
        flag = find_symbol(standard, "PWR_FLAG")
        if flag is None:
            raise SystemExit(f"PWR_FLAG not found in {KICAD_POWER_LIB}")
        root.append(copy.deepcopy(flag))

    TARGET.write_text(k.serialize(root) + "\n", encoding="utf-8", newline="\n")
    print(f"updated {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
