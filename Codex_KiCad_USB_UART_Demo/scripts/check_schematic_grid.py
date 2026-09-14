from pathlib import Path
import os
import re
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_PYTHON = PROJECT_ROOT / "tools" / "python"
HARDWARE_DIR = PROJECT_ROOT / "hardware" / "USB_UART_Bridge"
SCHEMATIC_PATHS = [
    HARDWARE_DIR / "USB_UART_Bridge.kicad_sch",
    HARDWARE_DIR / "Power.kicad_sch",
    HARDWARE_DIR / "Communicate.kicad_sch",
]

os.environ["KICAD_SYMBOL_DIR"] = r"D:\KiCad10.0\share\kicad\symbols"
os.environ["USERPROFILE"] = str(PROJECT_ROOT / ".pyhome")
os.environ["HOME"] = str(PROJECT_ROOT / ".pyhome")

sys.path.insert(0, str(TOOLS_PYTHON))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import kicad_sch_api as ksa

from grid_checks import (
    GRID_MM,
    find_close_text_anchors,
    find_different_net_intersections,
    find_invalid_net_names,
    find_invalid_wire_angles,
    find_labels_off_wires,
    find_missing_footprints,
    find_off_grid_items,
    find_out_of_bounds_items,
    find_overlapping_text_boxes,
    find_unexpected_global_labels,
)


def main() -> None:
    issues: list[str] = []
    totals = {
        "components": 0,
        "pins": 0,
        "wires": 0,
        "labels": 0,
        "no_connects": 0,
    }

    for schematic_path in SCHEMATIC_PATHS:
        schematic_text = schematic_path.read_text(encoding="utf-8")
        if re.search(r"\(pin_numbers\s*\(hide yes\)\s*\)", schematic_text):
            issues.append(f"{schematic_path.name}: hidden pin numbers found")
        schematic = ksa.load_schematic(schematic_path)
        sheet_issues = find_off_grid_items(schematic)
        sheet_issues.extend(find_missing_footprints(schematic))
        sheet_issues.extend(find_labels_off_wires(schematic))
        sheet_issues.extend(find_invalid_net_names(schematic))
        sheet_issues.extend(find_unexpected_global_labels(schematic))
        sheet_issues.extend(find_invalid_wire_angles(schematic))
        sheet_issues.extend(find_out_of_bounds_items(schematic))
        sheet_issues.extend(find_close_text_anchors(schematic))
        sheet_issues.extend(find_overlapping_text_boxes(schematic))
        sheet_issues.extend(find_different_net_intersections(schematic))
        issues.extend(f"{schematic_path.name}: {issue}" for issue in sheet_issues)
        totals["components"] += len(schematic.components)
        totals["pins"] += sum(
            len(schematic.list_component_pins(component.reference))
            for component in schematic.components
        )
        totals["wires"] += len(schematic.wires)
        totals["labels"] += len(schematic.labels) + len(schematic.hierarchical_labels)
        totals["no_connects"] += len(schematic.no_connects)

    if issues:
        for issue in issues:
            print(issue)
        raise SystemExit(
            f"Found {len(issues)} schematic validation issues at the "
            f"{GRID_MM} mm grid"
        )

    print(
        f"Grid check passed: {totals['components']} components, "
        f"{totals['pins']} pins, {totals['wires']} wires, "
        f"{totals['labels']} labels, {totals['no_connects']} no-connects."
    )


if __name__ == "__main__":
    main()
