#!/usr/bin/env python3
"""Print a summary of the assembled LA150C symbol library."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET = PROJECT_ROOT / "library" / "LA150C_RDIVER_V1.00.kicad_sym"


def main() -> int:
    library = k.read_library(TARGET)
    print(f"{TARGET.name}: {len(library)} symbols")
    for name in sorted(library):
        definition = library[name]
        props = {k.atom(p[1]): k.atom(p[2]) for p in k.direct_all(definition, "property")}
        pins = k.pin_numbers(definition)
        print(f"  {name:26s} ref={props.get('Reference', ''):3s} pins={len(pins):2d} value={props.get('Value', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
