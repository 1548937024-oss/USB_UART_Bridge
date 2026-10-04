#!/usr/bin/env python3
"""Private-library mapping and display-value rules for LA150C V1.00.

The page generators describe passives by their electrical value and package
(``Device:R`` + ``10K`` + ``0402 10K 1%``).  This module resolves the ones
that have a confirmed LCSC part in the classified library to that private
symbol, so the schematic, BOM and the classified library stay in sync.

Parts whose LCSC number has not been fixed yet stay on the generic KiCad
symbol and are listed in :data:`PENDING_PARTS`.  That is deliberate: the
LA150C BOM is still open on the DC-DC, TVS and reverse-protection parts, and
the schematic must not pretend otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class PrivatePart:
    symbol: str
    value: str
    note: str = ""


# Designators that keep the generic KiCad symbol because there is no
# confirmed purchase part yet.  The value shown on the schematic is still the
# design value; the note is what the reviewer needs to close.
PENDING_PARTS: dict[str, str] = {
    "Q1": "P-MOS 反接保护，型号待确认（母线 8~14 V，Vds ≥ 30 V）",
    "D1": "母线 TVS SMC/DO-214AB 18 V 档，具体型号待确认",
    "C1": "母线储能电容 ≥47 µF/25 V 低 ESR，型号待确认",
    "C2": "输出电容 2 × 22 µF，具体料号待确认",
}


# (generic class, displayed value, package) -> project-library symbol.
VALUE_PARTS: dict[tuple[str, str, str], str] = {
    ("R", "0R", "0201"): "RC0201FR-070RL",
    ("R", "0R", "0402"): "RC0402FR-070RL",
    ("R", "1K", "0201"): "RC0201FR-071KL",
    ("R", "1K", "0402"): "RC0402FR-071KL",
    ("R", "4.7K", "0201"): "RC0201FR-074K7L",
    ("R", "4.7K", "0402"): "RC0402FR-074K7L",
    ("R", "6.8K", "0201"): "RC0201FR-076K8L",
    ("R", "6.8K", "0402"): "RC0402FR-076K8L",
    ("R", "10R", "0201"): "RC0201FR-0710RL",
    ("R", "10K", "0201"): "RC0201FR-0710KL",
    ("R", "10K", "0402"): "RC0402FR-0710KL",
    ("R", "15K", "0402"): "RC0402FR-0715KL",
    ("R", "100R", "0201"): "RC0201FR-07100RL",
    ("R", "20K", "0402"): "RC0402FR-0720KL",
    ("R", "22K", "0402"): "RC0402FR-0722KL",
    ("R", "26.1K", "0201"): "RC0201DR-0726K1L",
    ("R", "47K", "0201"): "RC0201FR-0747KL",
    ("R", "100K", "0402"): "RC0402FR-07100KL",
    ("R", "100K", "0603"): "RC0603FR-07100KL",
    ("R", "10K NTC", "0402"): "NCP15XH103F03RC",
    ("C", "100pF", "0201"): "FN03N100J500PLG",
    ("C", "2.2nF", "0402"): "CC0402KRX7R9BB222",
    ("C", "10nF", "0402"): "CC0402KRX7R0BB103",
    ("C", "100nF", "0201"): "GRM033Z71C104KE14D",
    ("C", "100nF", "0402"): "GRM155R71H104KE14D",
    ("C", "100nF", "0603"): "CL10B104KC8NNNC",
    ("C", "1uF", "0402"): "CL05Y105KP6VPNC",
    ("C", "4.7uF", "0603"): "CL10A475KP8NNNC",
    ("C", "10uF", "0603"): "CL10B106MQ8NRNC",
    ("C", "10uF", "1210"): "GRM32EC72A106KE05L",
    ("L", "600R", "0402"): "BLM15AG601SN1D",
}


# Polarity matters for two-terminal protection parts: pin 1 is the cathode.
PART_BY_REFERENCE: dict[str, PrivatePart] = {
    "D2": PrivatePart("PESD1CAN,215", "PESD1CAN,215"),
}


DISPLAY_VALUE_OVERRIDES = {
    "4K7": "4.7K",
}


GENERIC_PREFIXES = ("Device:", "Transistor_FET:")
PACKAGE_RE = re.compile(r"^\s*(0201|0402|0603|0805|1206|1210)\b")


def generic_class(lib_id: str) -> str:
    if lib_id == "Device:R":
        return "R"
    if lib_id == "Device:C":
        return "C"
    if lib_id == "Device:L":
        return "L"
    if lib_id == "Device:LED":
        return "LED"
    if lib_id == "Device:D":
        return "D"
    if lib_id == "Device:D_TVS":
        return "D_TVS"
    if lib_id == "Transistor_FET:Q_PMOS_GSD":
        return "MOS"
    return ""


def package_from_description(description: str) -> str:
    match = PACKAGE_RE.match(description)
    return match.group(1) if match else ""


def display_value(value: str) -> str:
    return DISPLAY_VALUE_OVERRIDES.get(value, value)


def resolve(
    lib_id: str,
    reference: str,
    value: str,
    description: str,
) -> PrivatePart | None:
    """Resolve one generic schematic component to a private-library symbol.

    Returns ``None`` when the part has no confirmed LCSC counterpart; the
    caller then keeps the generic KiCad symbol and records the open item.
    """
    if not lib_id.startswith(GENERIC_PREFIXES):
        return None
    if reference in PENDING_PARTS:
        return None
    if reference in PART_BY_REFERENCE:
        return PART_BY_REFERENCE[reference]

    kind = generic_class(lib_id)
    package = package_from_description(description)
    if not kind or not package:
        return None
    symbol = VALUE_PARTS.get((kind, value, package))
    if symbol is None:
        return None
    return PrivatePart(symbol=symbol, value=display_value(value))


def normalized_symbol_names() -> set[str]:
    """Symbols whose two-terminal geometry must match the KiCad templates."""
    names = set(VALUE_PARTS.values())
    names.update(part.symbol for part in PART_BY_REFERENCE.values())
    names.update({"PESD1CAN,215", "SMBJ58CA", "XL-1005UGC"})
    return names
