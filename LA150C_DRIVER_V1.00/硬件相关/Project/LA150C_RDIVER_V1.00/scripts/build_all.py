#!/usr/bin/env python3
"""Regenerate the whole LA150C RDIVER V1.00 schematic set in one pass."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

STEPS = [
    ("build_sheet_template", None),
    ("assemble_library", None),
    ("build_custom_symbols", None),
    ("build_project", None),
    ("build_power_page", None),
    ("build_mcu_page", None),
    ("build_encoder_page", None),
    ("build_communication_page", None),
    ("build_motor_page", None),
    ("build_top_page", None),
]


def main() -> int:
    for name, _ in STEPS:
        module = importlib.import_module(name)
        print(f"===== {name} =====")
        result = module.main()
        if result:
            return int(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
