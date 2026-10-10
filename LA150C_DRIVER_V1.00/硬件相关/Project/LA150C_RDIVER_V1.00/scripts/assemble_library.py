#!/usr/bin/env python3
"""Assemble the LA150C V1.00 project symbol library.

Ported from the MicroDriver V2.10 external-driver workflow.  The project
keeps one self-contained ``.kicad_sym`` so the schematic never references a
user-private or KiCad-installation path.  Sources, in order (later wins):

1. KiCad standard Device / Transistor_FET symbols used directly;
2. the classified LCSC libraries built for this repository;
3. the power-symbol set, renamed to the LA150C net names;
4. the custom symbols authored in ``build_custom_symbols.py``.

Two-terminal passives imported from the classified library are re-drawn on
the KiCad template geometry so that ``Device:R`` / ``Device:C`` pin
coordinates used by the page generators land exactly on the placed symbol.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402
import private_parts as pp  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET = PROJECT_ROOT / "library" / "LA150C_RDIVER_V1.00.kicad_sym"

CLASSIFIED_ROOT = Path(
    r"D:\办公相关\项目相关\三花\03-灵巧手项目\O-硬件设计"
    r"\Library\Private\LCSC_Classified\libraries"
)
KICAD_SYMBOLS = Path(r"D:\KiCad10.0\share\kicad\symbols")


# Generic geometry templates.  The custom page builders place generic
# Device:R/C/L/D/D_TVS symbols, so the private counterparts must share their
# pin geometry.
TEMPLATE_NAMES = ("R", "C", "L", "D", "D_TVS", "LED")

STANDARD_SYMBOLS = [
    ("Device", "Device.kicad_sym", "R"),
    ("Device", "Device.kicad_sym", "C"),
    ("Device", "Device.kicad_sym", "L"),
    ("Device", "Device.kicad_sym", "D"),
    ("Device", "Device.kicad_sym", "D_TVS"),
    ("Device", "Device.kicad_sym", "LED"),
    ("Connector", "Connector.kicad_sym", "TestPoint"),
    ("Transistor_FET", "Transistor_FET.kicad_sym", "Q_PMOS_GSD"),
]


# Symbols pulled from the classified LCSC libraries, keyed by the exact name
# used in that library and by the lib_id the page generators reference.
CLASSIFIED_SYMBOLS: list[tuple[str, str]] = [
    ("Interface", "TCAN3413DDFR_C30111221"),
    ("Sensors", "NCP15XH103F03RC"),
    ("Transistors", "PESD1CAN,215"),
    ("Circuit Protection", "SMF16CA"),
    ("Crystals, Oscillators, Resonators", "CSTNE8M00G52A000R0"),
    ("Magnetic Sensors", "MT6701QT-STD_C2913974"),
    # passives with confirmed LCSC parts
    ("Resistors", "RC0201FR-070RL"),
    ("Resistors", "RC0402FR-070RL"),
    ("Resistors", "RC0201FR-071KL"),
    ("Resistors", "RC0402FR-071KL"),
    ("Resistors", "RC0201FR-074K7L"),
    ("Resistors", "RC0402FR-074K7L"),
    ("Resistors", "RC0402FR-0715KL"),
    ("Resistors", "RC0201FR-076K8L"),
    ("Resistors", "RC0402FR-076K8L"),
    ("Resistors", "RC0201FR-0710RL"),
    ("Resistors", "RC0201FR-0710KL"),
    ("Resistors", "RC0402FR-0710KL"),
    ("Resistors", "RC0201FR-07100RL"),
    ("Resistors", "RC0402FR-0720KL"),
    ("Resistors", "RC0402FR-0722KL"),
    ("Resistors", "RC0201DR-0726K1L"),
    ("Resistors", "RC0201FR-0747KL"),
    ("Resistors", "RC0402FR-07100KL"),
    ("Resistors", "RC0603FR-07100KL"),
    ("Capacitors", "GRM033Z71C104KE14D"),
    ("Capacitors", "GRM155R71H104KE14D"),
    ("Capacitors", "CL10B104KC8NNNC"),
    ("Capacitors", "GRM188Z71A106KA73D"),
    ("Capacitors", "CL10B105KB8NQNC"),
    ("Capacitors", "CL03C101JB3NNNC"),
    ("Capacitors", "CL05Y105KP6VPNC"),
    ("Capacitors", "CL10A475KP8NNNC"),
    ("Capacitors", "CL10B106MQ8NRNC"),
    ("Capacitors", "GRM32EC72A106KE05L"),
    ("Capacitors", "FN03N100J500PLG"),
    ("Capacitors", "CC0402KRX7R9BB222"),
    ("Capacitors", "CC0402KRX7R0BB103"),
    ("Capacitors", "CGA4J1X7S1E106KT0Y0N"),
    ("Capacitors", "C1005X7S1A225KT000E"),
    ("Filters", "BLM15AG601SN1D"),
]


# DE5VS06BA was converted before the active Circuit Protection library was
# rebuilt and currently remains in the backup file.  Keep the source
# explicit so the project library stays reproducible without editing the
# shared classified library.
MANUAL_SYMBOLS: list[tuple[str, str, str]] = [
    ("Circuit Protection", "Circuit Protection.bak", "DE5VS06BA"),
]


# Project net names mapped to the KiCad standard power-symbol graphics.
# (library symbol, displayed Value) -> project symbol name
POWER_SYMBOLS: dict[tuple[str, str], str] = {
    ("GND", "GND"): "GND",
    ("GNDA", "AGND"): "AGND",
    ("GNDPWR", "PGND"): "PGND",
    ("+3.3V", "PWR_3V3"): "PWR_3V3",
    ("+3.3VA", "PWR_3V3A"): "PWR_3V3A",
    ("+5V", "PWR_5V"): "PWR_5V",
    ("VBUS", "VBUS"): "VBUS",
    ("VBUS", "VBUS_IN"): "VBUS_IN",
    ("PWR_FLAG", "PWR_FLAG"): "PWR_FLAG",
}


def classified_path(category: str) -> Path:
    return CLASSIFIED_ROOT / category / f"{category}.kicad_sym"


def collect_groups() -> tuple[dict[str, list[k.Node]], list[str]]:
    merged: dict[str, list[k.Node]] = {}

    # 1. KiCad standard symbols, used directly for generic passives.
    for _nickname, filename, name in STANDARD_SYMBOLS:
        library = k.read_library(KICAD_SYMBOLS / filename)
        if name not in library:
            raise SystemExit(f"{name} not found in {filename}")
        merged[name] = copy.deepcopy(library[name])

    # 2. Classified parts.
    missing: list[str] = []
    for category, name in CLASSIFIED_SYMBOLS:
        library = k.read_library(classified_path(category))
        if name not in library:
            # A classified part that has not been imported yet must not break
            # the whole build; the page generator falls back to the generic
            # KiCad symbol when the private counterpart is unavailable.
            missing.append(f"{category}/{name}")
            continue
        merged[name] = copy.deepcopy(library[name])

    # 2b. Manually retained classified parts.
    for category, filename, name in MANUAL_SYMBOLS:
        path = classified_path(category).with_name(filename)
        library = k.read_library(path)
        if name not in library:
            missing.append(f"{category}/{filename}:{name}")
            continue
        merged[name] = copy.deepcopy(library[name])

    # 3. Power symbols, renamed to the LA150C net names.
    power_library = k.read_library(KICAD_SYMBOLS / "power.kicad_sym")
    for (source, value), target in POWER_SYMBOLS.items():
        if source not in power_library:
            raise SystemExit(f"power:{source} not found")
        node = copy.deepcopy(power_library[source])
        rename_symbol(node, target)
        for prop in k.direct_all(node, "property"):
            if k.atom(prop[1]) == "Value":
                prop[2] = k.quote(value)
        merged[target] = node

    return merged, missing


def property_map(node: list[k.Node]) -> dict[str, list[k.Node]]:
    return {
        k.atom(prop[1]): prop
        for prop in k.direct_all(node, "property")
        if len(prop) >= 3
    }


def rotate_symbol(node: k.Node, angle: float = 90) -> None:
    """Rotate symbol-local geometry and pins counter-clockwise."""
    if not isinstance(node, list):
        return
    if node and node[0] in {"at", "start", "end", "center", "mid"} and len(node) >= 3:
        x = float(k.atom(node[1]))
        y = float(k.atom(node[2]))
        node[1] = k.number(-y)
        node[2] = k.number(x)
        if node[0] == "at" and len(node) >= 4:
            node[3] = k.number((float(k.atom(node[3])) + angle) % 360)
        return
    if node and node[0] == "xy" and len(node) >= 3:
        x = float(k.atom(node[1]))
        y = float(k.atom(node[2]))
        node[1] = k.number(-y)
        node[2] = k.number(x)
        return
    for item in node:
        if isinstance(item, list):
            rotate_symbol(item, angle)


def rename_symbol(node: list[k.Node], name: str) -> None:
    old_name = k.atom(node[1])
    node[1] = k.quote(name)
    for child in node[1:]:
        if isinstance(child, list) and child and child[0] == "symbol":
            child_name = k.atom(child[1])
            if child_name.startswith(old_name):
                child[1] = k.quote(name + child_name[len(old_name):])


def set_pin_type(node: k.Node, kind: str = "passive") -> None:
    if not isinstance(node, list):
        return
    if node and node[0] == "pin" and len(node) > 1:
        node[1] = kind
    for item in node:
        if isinstance(item, list):
            set_pin_type(item, kind)


def set_pin_types(node: k.Node, mapping: dict[str, str]) -> None:
    """Set pin electrical types by pin number."""
    if not isinstance(node, list):
        return
    if node and node[0] == "pin":
        number_node = k.direct(node, "number")
        if number_node is not None and len(number_node) >= 2:
            number = k.atom(number_node[1])
            if number in mapping:
                node[1] = mapping[number]
    for item in node:
        if isinstance(item, list):
            set_pin_types(item, mapping)


def passive_category(name: str, source: list[k.Node]) -> str | None:
    props = property_map(source)
    footprint = k.atom(props.get("Footprint", ["property", "", ""])[2])
    description = " ".join(
        k.atom(props[key][2])
        for key in ("Description", "ki_description", "ki_keywords")
        if key in props
    )
    if footprint.startswith("Resistors:") or "NTC" in description:
        return "R"
    if footprint.startswith("Capacitors:"):
        return "C"
    if footprint.startswith(("Inductors:", "Filters:")):
        return "L"
    if footprint.startswith("Optoelectronics:") and "LED" in (name + description):
        return "LED"
    if footprint.startswith("Diodes:"):
        return "D_TVS" if ("TVS" in description or "ESD" in description) else "D"
    return None


def template_properties(
    name: str, source: list[k.Node], template: list[k.Node]
) -> list[k.Node]:
    """Keep the classified metadata while adopting the template geometry."""
    source_props = property_map(source)
    template_props = property_map(template)
    ordered: list[str] = []
    for prop in k.direct_all(source, "property"):
        key = k.atom(prop[1])
        if key not in ordered:
            ordered.append(key)
    for key in template_props:
        if key not in ordered:
            ordered.append(key)
    result: list[k.Node] = []
    for key in ordered:
        prop = source_props.get(key) or template_props[key]
        result.append(copy.deepcopy(prop))
    by_key = {k.atom(prop[1]): prop for prop in result}
    if "Description" not in by_key:
        description = by_key.get("ki_description")
        if description is not None:
            node = copy.deepcopy(template_props.get("Description", template_props["Value"]))
            node[1] = k.quote("Description")
            node[2] = k.quote(k.atom(description[2]))
            result.append(node)
    if "MPN" not in by_key:
        node = copy.deepcopy(template_props.get("Value", template_props["Reference"]))
        node[1] = k.quote("MPN")
        node[2] = k.quote(name)
        result.append(node)
    return result


def normalise_two_terminal(
    name: str, source: list[k.Node], templates: dict[str, list[k.Node]]
) -> list[k.Node] | None:
    pins = k.pin_definitions(source)
    if len(pins) != 2 or set(pins) != {"1", "2"}:
        return None
    category = passive_category(name, source)
    if category is None or category not in templates:
        return None
    node = copy.deepcopy(templates[category])
    if category in {"LED", "D", "D_TVS"}:
        rotate_symbol(node)
    rename_symbol(node, name)
    node[:] = [
        item
        for item in node
        if not (isinstance(item, list) and item and item[0] == "property")
    ]
    insert_at = 1
    while insert_at < len(node) and not isinstance(node[insert_at], list):
        insert_at += 1
    for prop in template_properties(name, source, templates[category]):
        node.insert(insert_at, prop)
        insert_at += 1
    return node


def main() -> int:
    merged, missing = collect_groups()
    templates = {name: merged[name] for name in TEMPLATE_NAMES if name in merged}

    normalised: list[str] = []
    for name in list(merged):
        if name in templates:
            continue
        source = merged[name]
        if (
            name in pp.normalized_symbol_names()
            or passive_category(name, source) is not None
        ):
            node = normalise_two_terminal(name, source, templates)
            if node is not None:
                set_pin_type(node, "passive")
                merged[name] = node
                normalised.append(name)

    # Connector and ESD parts import with unspecified pin types; normalise
    # them to passive so ERC does not flag pin-type conflicts.
    for name in (
        "PESD1CAN,215",
        "SMF16CA",
        "DE5VS06BA",
        "CSTNE8M00G52A000R0",
    ):
        if name in merged:
            set_pin_type(merged[name], "passive")

    # The classified MT6701 symbol carries unspecified pin types.  Define
    # the interface explicitly so ERC checks the real supply/ground and does
    # not warn on every SSI net.
    mt6701 = merged.get("MT6701QT-STD_C2913974")
    if mt6701 is not None:
        set_pin_type(mt6701, "passive")
        set_pin_types(mt6701, {"13": "power_in", "16": "power_in", "17": "passive"})

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

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(k.serialize(root) + "\n", encoding="utf-8", newline="\n")
    print(f"{TARGET.name}: {len(merged)} symbols")
    print(f"  two-terminal geometry normalised: {len(normalised)}")
    if missing:
        print(f"  classified parts not present yet ({len(missing)}): {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
