#!/usr/bin/env python3
"""Hide pin-name text on resistor and capacitor symbols without hiding pin numbers."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol_libraries", nargs="+", type=Path)
    return parser.parse_args()


def top_level_symbol_blocks(text: str) -> list[tuple[int, int, str]]:
    matches = list(re.finditer(r'(?m)^([\t ]+)\(symbol\s+"', text))
    if not matches:
        return []

    depths = [len(match.group(1).expandtabs(4)) for match in matches]
    top_depth = min(depths)
    blocks: list[tuple[int, int, str]] = []

    for match, depth in zip(matches, depths):
        if depth != top_depth:
            continue

        start = match.start() + match.group(0).index("(")
        parentheses = 0
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
                parentheses += 1
            elif character == ")":
                parentheses -= 1
                if parentheses == 0:
                    blocks.append((start, index + 1, text[start : index + 1]))
                    break

    return blocks


def child_indent(block: str, token: str) -> str:
    match = re.search(rf'(?m)^([\t ]+)\({re.escape(token)}\b', block)
    if not match:
        raise ValueError(f"Could not find child {token!r}")
    return match.group(1)


def balanced_expression_end(text: str, start: int) -> int:
    parentheses = 0
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
            parentheses += 1
        elif character == ")":
            parentheses -= 1
            if parentheses == 0:
                return index + 1
    raise ValueError("Unbalanced parentheses in pin_names")


def hidden_pin_names_block(indent: str, offset: str) -> str:
    return (
        f"{indent}(pin_names\n"
        f"{indent}\t(offset {offset})\n"
        f"{indent}\t(hide yes)\n"
        f"{indent})"
    )


def hide_pin_names_in_file(path: Path) -> int:
    original_text = path.read_text(encoding="utf-8")
    text = original_text
    top_level_symbols = top_level_symbol_blocks(text)
    if not top_level_symbols:
        raise ValueError(f"No top-level symbols found in {path}")

    pin_names = list(re.finditer(r"(?m)^[\t ]+\(pin_names\b", text))
    for match in reversed(pin_names):
        start = match.start()
        if start > 0 and text[start - 1] == "\n":
            start -= 1
        end = balanced_expression_end(text, start)
        text = text[:start] + text[end:]

    on_board_pattern = re.compile(r"(?m)^([\t ]+)\(on_board\s+yes\)\s*$")
    symbol_count = len(on_board_pattern.findall(text))
    text = on_board_pattern.sub(
        lambda match: (
            match.group(0)
            + "\n"
            + hidden_pin_names_block(match.group(1), "0")
        ),
        text,
    )
    path.write_text(text, encoding="utf-8")
    return symbol_count if text != original_text else 0


def main() -> int:
    args = parse_args()
    total = 0
    for path in args.symbol_libraries:
        changed = hide_pin_names_in_file(path.resolve())
        total += changed
        print(f"{path}: hidden pin names updated in {changed} symbols")
    print(f"Updated {total} symbols.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
