#!/usr/bin/env python3
"""Shared metadata helpers for the classified LCSC KiCad libraries."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping


PDF_REFERENCE = re.compile(r"\.pdf(?:$|[?#])", re.IGNORECASE)
PARTIAL_STATUSES = {
    "CLASSIFIED_PARTIAL",
    "LCSC_CONFLICT",
    "LOOKUP_FAILED",
    "PENDING_ENRICHMENT",
}

CORE_SYMBOL_FIELDS = (
    "Datasheet",
    "Manufacturer",
    "MPN",
    "LCSC Part",
    "ki_keywords",
)
OPTIONAL_SYMBOL_FIELDS = (
    "DatasheetRev",
    "DatasheetDate",
    "LocalDatasheet",
)


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def is_pdf_reference(value: object) -> bool:
    text = clean(value)
    return bool(text and PDF_REFERENCE.search(text))


def is_product_page(value: object) -> bool:
    text = clean(value).lower()
    return "product-detail" in text or "/global.html" in text


def is_partial(row: Mapping[str, str]) -> bool:
    return clean(row.get("ReviewStatus")).upper() in PARTIAL_STATUSES


def extract_top_level_blocks(text: str, token: str = "symbol") -> list[str]:
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


def property_value(block: str, property_name: str) -> str:
    match = re.search(
        rf'\(property\s+"{re.escape(property_name)}"\s+"((?:[^"\\]|\\.)*)"',
        block,
    )
    return match.group(1) if match else ""


def has_property(block: str, property_name: str) -> bool:
    return re.search(
        rf'\(property\s+"{re.escape(property_name)}"\s+"',
        block,
    ) is not None


def symbol_name(block: str) -> str:
    match = re.search(r'\(symbol\s+"([^"]+)"', block)
    return match.group(1) if match else ""


def escape_sexpr_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def set_property(block: str, property_name: str, value: str) -> str:
    escaped_name = escape_sexpr_string(property_name)
    escaped_value = escape_sexpr_string(value)
    pattern = re.compile(
        rf'(\(property\s+"{re.escape(escaped_name)}"\s+)"(?:[^"\\]|\\.)*"',
        flags=re.MULTILINE,
    )
    replacement = rf'\1"{escaped_value}"'
    updated, count = pattern.subn(replacement, block, count=1)
    if count:
        return updated

    property_match = re.search(r'(?m)^([\t ]+)\(property\s+"', block)
    nested_match = re.search(r'(?m)^[\t ]+\(symbol\s+"', block)
    if not property_match or not nested_match:
        raise ValueError(f"Could not add property {property_name!r}")

    indent = property_match.group(1)
    insertion = (
        f'{indent}(property "{escaped_name}" "{escaped_value}"\n'
        f'{indent}\t(at 0 0 0)\n'
        f'{indent}\t(hide yes)\n'
        f'{indent}\t(effects (font (size 1.27 1.27)))\n'
        f'{indent})\n'
    )
    return block[: nested_match.start()] + insertion + block[nested_match.start() :]


def metadata_properties(row: Mapping[str, str]) -> dict[str, str]:
    return {
        "Value": clean(row.get("Value")),
        "Datasheet": clean(row.get("Datasheet")),
        "DatasheetRev": clean(row.get("DatasheetRev")),
        "DatasheetDate": clean(row.get("DatasheetDate")),
        "LocalDatasheet": clean(row.get("LocalDatasheet")),
        "Manufacturer": clean(row.get("Manufacturer")),
        "MPN": clean(row.get("MPN")),
        "LCSC Part": clean(row.get("LCSC")).upper(),
        "ki_keywords": clean(row.get("Category")),
        "ki_description": clean(row.get("Description")),
        "Description": clean(row.get("Description")),
    }


def update_symbol_library_metadata(
    symbol_library: Path,
    rows_by_lcsc: Mapping[str, Mapping[str, str]],
) -> int:
    original_text = symbol_library.read_text(encoding="utf-8")
    text = original_text
    changed_symbols = 0

    for block in extract_top_level_blocks(text):
        lcsc = clean(property_value(block, "LCSC Part")).upper()
        row = rows_by_lcsc.get(lcsc)
        if not row:
            continue

        updated_block = block
        properties = metadata_properties(row)
        for name, value in properties.items():
            if value or has_property(updated_block, name):
                updated_block = set_property(updated_block, name, value)

        if updated_block != block:
            text = text.replace(block, updated_block, 1)
            changed_symbols += 1

    if text != original_text:
        symbol_library.write_text(text, encoding="utf-8")

    return changed_symbols


def iter_symbol_libraries(library_root: Path) -> list[Path]:
    return sorted(library_root.rglob("*.kicad_sym"))


def remove_model_references(kicad_mod: Path) -> int:
    text = kicad_mod.read_text(encoding="utf-8")
    models = extract_top_level_blocks(text, "model")
    for model in models:
        text = text.replace(model, "", 1)
    if models:
        text = re.sub(r"\n{3,}", "\n\n", text)
        kicad_mod.write_text(text, encoding="utf-8")
    return len(models)
