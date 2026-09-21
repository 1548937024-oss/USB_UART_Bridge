#!/usr/bin/env python3
"""Convert pending parts from KiCad's standard symbol and footprint libraries."""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StandardMapping:
    lcsc: str
    category: str
    source_symbol_library: str
    source_symbol: str
    source_footprint_library: str
    source_footprint: str
    output_symbol: str = ""
    output_footprint: str = ""
    reference: str = ""


STANDARD_MAPPINGS = (
    StandardMapping(
        "C474825",
        "Resistors",
        "Device",
        "R",
        "Resistor_SMD",
        "R_0201_0603Metric",
    ),
    StandardMapping(
        "C5224095",
        "Diodes",
        "Device",
        "D_Zener",
        "Diode_SMD",
        "D_SOD-123",
    ),
    StandardMapping(
        "C561710",
        "Capacitors",
        "Device",
        "C",
        "Capacitor_SMD",
        "C_0201_0603Metric",
    ),
    StandardMapping(
        "C76884",
        "Filters",
        "Device",
        "FerriteBead",
        "Inductor_SMD",
        "L_0402_1005Metric",
    ),
    StandardMapping(
        "C76941",
        "Capacitors",
        "Device",
        "C",
        "Capacitor_SMD",
        "C_0201_0603Metric",
    ),
    StandardMapping(
        "C77020",
        "Capacitors",
        "Device",
        "C",
        "Capacitor_SMD",
        "C_0402_1005Metric",
    ),
    StandardMapping(
        "C77131",
        "Sensors",
        "Device",
        "Thermistor_NTC",
        "Resistor_SMD",
        "R_0402_1005Metric",
    ),
    StandardMapping(
        "C77623",
        "Resistors",
        "Device",
        "R",
        "Resistor_SMD",
        "R_0201_0603Metric",
    ),
    StandardMapping(
        "C78879",
        "Diodes",
        "Diode",
        "BAV99",
        "Package_TO_SOT_SMD",
        "SOT-323_SC-70",
    ),
    StandardMapping(
        "C82868",
        "Resistors",
        "Device",
        "R",
        "Resistor_SMD",
        "R_0402_1005Metric",
    ),
    StandardMapping(
        "C851693",
        "Resistors",
        "Device",
        "R",
        "Resistor_SMD",
        "R_0201_0603Metric",
    ),
    StandardMapping(
        "C93940",
        "Resistors",
        "Device",
        "R",
        "Resistor_SMD",
        "R_0402_1005Metric",
    ),
    StandardMapping(
        "C93942",
        "Resistors",
        "Device",
        "R",
        "Resistor_SMD",
        "R_0402_1005Metric",
    ),
    StandardMapping(
        "C965793",
        "Optoelectronics",
        "Device",
        "LED",
        "LED_SMD",
        "LED_0402_1005Metric",
    ),
    StandardMapping(
        "C9900198844",
        "Circuit Protection",
        "Device",
        "D_TVS",
        "Diode_SMD",
        "D_SOD-323",
    ),
    StandardMapping(
        "C9900301658",
        "Circuit Protection",
        "Device",
        "D_TVS",
        "Diode_SMD",
        "D_0201_0603Metric",
        output_symbol="DE5VS06BA",
    ),
)

SYMBOL_HEADER = """(kicad_symbol_lib
  (version 20251024)
  (generator "kicad_symbol_editor")
  (generator_version "10.0")
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-index", type=Path, required=True)
    parser.add_argument("--library-root", type=Path, required=True)
    parser.add_argument("--state-file", type=Path, required=True)
    parser.add_argument("--kicad-root", type=Path)
    return parser.parse_args()


def find_kicad_root(explicit: Path | None) -> Path:
    candidates = []
    if explicit:
        candidates.append(explicit)
    candidates.extend((Path(r"D:\KiCad10.0"), Path(r"C:\Program Files\KiCad\10.0")))
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("KiCad 10 installation was not found")


def read_json(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def extract_top_level_blocks(text: str, token: str) -> list[str]:
    starts = list(re.finditer(rf'(?m)^\s*\({re.escape(token)}\s+"', text))
    blocks: list[str] = []
    for match in starts:
        start = match.start() + match.group(0).index("(")
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            character = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    in_string = False
                continue
            if character == '"':
                in_string = True
            elif character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    blocks.append(text[start : index + 1])
                    break
    return blocks


def symbol_name(block: str) -> str:
    match = re.search(r'\(symbol\s+"([^"]+)"', block)
    return match.group(1) if match else ""


def source_symbol_block(source_library: Path, source_name: str) -> str:
    blocks = extract_top_level_blocks(
        source_library.read_text(encoding="utf-8"),
        "symbol",
    )
    for block in blocks:
        if symbol_name(block) == source_name:
            return block
    raise ValueError(f"Symbol {source_name!r} was not found in {source_library}")


def escape_sexpr_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def set_property(block: str, property_name: str, value: str) -> str:
    escaped = escape_sexpr_string(value)
    pattern = re.compile(
        rf'(\(property\s+"{re.escape(property_name)}"\s+)"(?:[^"\\]|\\.)*"',
        flags=re.MULTILINE,
    )
    replacement = rf'\1"{escaped}"'
    updated, count = pattern.subn(replacement, block, count=1)
    if count:
        return updated

    insertion = (
        f'    (property\n'
        f'      "{property_name}"\n'
        f'      "{escaped}"\n'
        f'      (at 0 0 0)\n'
        f'      (hide yes)\n'
        f'      (effects (font (size 1.27 1.27)))\n'
        f'    )\n'
    )
    nested = re.search(r'(?m)^[\t ]+\(symbol\s+"', block)
    if not nested:
        raise ValueError(f"Could not add property {property_name!r}")
    return block[: nested.start()] + insertion + block[nested.start() :]


def rename_symbol(block: str, source_name: str, output_name: str) -> str:
    updated = re.sub(
        rf'(\(symbol\s+"){re.escape(source_name)}"',
        rf'\1{escape_sexpr_string(output_name)}"',
        block,
        count=1,
    )
    return updated.replace(f'"{source_name}_', f'"{escape_sexpr_string(output_name)}_')


def clean_symbol_block(block: str) -> str:
    text = block.strip()
    text = re.sub(r'(?m)^\s*\(property\s+"ki_fp_filters".*?\)\s*\n', "", text)
    return text


def convert_symbol(
    row: dict[str, str],
    mapping: StandardMapping,
    kicad_root: Path,
    library_root: Path,
) -> tuple[str, str]:
    source_library = (
        kicad_root / "share" / "kicad" / "symbols"
        / f"{mapping.source_symbol_library}.kicad_sym"
    )
    block = source_symbol_block(source_library, mapping.source_symbol)

    output_symbol = (
        mapping.output_symbol
        or (row.get("MPN") or "").strip()
        or row["LCSC"].strip()
    )
    output_footprint = mapping.output_footprint or mapping.source_footprint
    category_dir = library_root / mapping.category
    category_dir.mkdir(parents=True, exist_ok=True)
    symbol_library = category_dir / f"{mapping.category}.kicad_sym"

    if not symbol_library.is_file():
        symbol_library.write_text(SYMBOL_HEADER + ")\n", encoding="utf-8")

    block = rename_symbol(block, mapping.source_symbol, output_symbol)
    properties = {
        "Reference": mapping.reference or None,
        "Value": (row.get("Value") or "").strip() or output_symbol,
        "Footprint": f"{mapping.category}:{output_footprint}",
        "Datasheet": (row.get("Datasheet") or "").strip()
        or (row.get("LCSC_URL") or "").strip(),
        "Manufacturer": (row.get("Manufacturer") or "").strip(),
        "MPN": (row.get("MPN") or "").strip(),
        "LCSC Part": row["LCSC"].strip(),
        "ki_keywords": (row.get("Category") or "").strip(),
        "ki_description": (row.get("Description") or "").strip(),
    }
    for name, value in properties.items():
        if value is not None:
            block = set_property(block, name, value)
    block = clean_symbol_block(block)

    library_text = symbol_library.read_text(encoding="utf-8").rstrip()
    existing_blocks = extract_top_level_blocks(library_text, "symbol")
    for existing in existing_blocks:
        if symbol_name(existing) == output_symbol:
            library_text = library_text.replace(existing, "", 1).rstrip()
    if library_text.endswith(")"):
        library_text = library_text[:-1].rstrip()
    indented_block = "\n".join(f"  {line}" for line in block.splitlines())
    library_text = f"{library_text}\n\n{indented_block}\n)\n"
    symbol_library.write_text(library_text, encoding="utf-8")

    source_footprint = (
        kicad_root
        / "share"
        / "kicad"
        / "footprints"
        / f"{mapping.source_footprint_library}.pretty"
        / f"{mapping.source_footprint}.kicad_mod"
    )
    if not source_footprint.is_file():
        raise FileNotFoundError(source_footprint)

    footprint_dir = category_dir / f"{mapping.category}.pretty"
    footprint_dir.mkdir(parents=True, exist_ok=True)
    output_footprint_path = footprint_dir / f"{output_footprint}.kicad_mod"
    footprint_text = source_footprint.read_text(encoding="utf-8")
    footprint_text = re.sub(
        rf'^\(footprint\s+"{re.escape(mapping.source_footprint)}"',
        f'(footprint "{escape_sexpr_string(output_footprint)}"',
        footprint_text,
        count=1,
    )
    output_footprint_path.write_text(footprint_text, encoding="utf-8")
    return output_symbol, output_footprint


def main() -> int:
    args = parse_args()
    library_index = args.library_index.resolve()
    library_root = args.library_root.resolve()
    state_path = args.state_file.resolve()
    kicad_root = find_kicad_root(args.kicad_root)

    with library_index.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    rows_by_lcsc = {
        (row.get("LCSC") or "").strip().upper(): row
        for row in rows
    }
    state = read_json(state_path)
    converted = 0
    missing: list[str] = []

    for mapping in STANDARD_MAPPINGS:
        row = rows_by_lcsc.get(mapping.lcsc)
        if row is None:
            missing.append(mapping.lcsc)
            continue
        if row.get("ConversionStatus") == "CONVERTED":
            continue
        output_symbol, output_footprint = convert_symbol(
            row,
            mapping,
            kicad_root,
            library_root,
        )
        state[mapping.lcsc] = "converted"
        write_json(state_path, state)
        converted += 1
        print(
            f"{mapping.lcsc} -> {mapping.category}: "
            f"{output_symbol} / {output_footprint}",
            flush=True,
        )

    if missing:
        print("Missing library-index rows: " + ", ".join(missing))
        return 1

    print(f"Converted {converted} parts from standard KiCad libraries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
