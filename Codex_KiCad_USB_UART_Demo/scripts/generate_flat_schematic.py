from pathlib import Path
import math
import os
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_PYTHON = PROJECT_ROOT / "tools" / "python"
HARDWARE_DIR = PROJECT_ROOT / "hardware" / "USB_UART_Bridge"
SCHEMATIC_PATH = HARDWARE_DIR / "USB_UART_Bridge.kicad_sch"

os.environ.setdefault("KICAD_SYMBOL_DIR", r"D:\KiCad10.0\share\kicad\symbols")
os.environ["USERPROFILE"] = str(PROJECT_ROOT / ".pyhome")
os.environ["HOME"] = str(PROJECT_ROOT / ".pyhome")

sys.path.insert(0, str(TOOLS_PYTHON))

import yaml
import kicad_sch_api as ksa
from kicad_sch_api.core.pin_utils import get_component_pin_info
from grid_checks import GRID_MM, assert_schematic_on_grid, snap_point


POSITIONS = {
    # USB input and USB-side power, left to right.
    "J1": (45.72, 80.01),
    "U2": (100.33, 80.01),
    "F1": (45.72, 30.48),
    "C1": (68.58, 30.48),
    "R1": (90.17, 110.49),
    "R2": (105.41, 110.49),
    # USB-UART bridge and local status indicators.
    "U1": (134.62, 85.09),
    "C2": (111.76, 35.56),
    "C3": (121.92, 35.56),
    "C4": (132.08, 35.56),
    "C5": (142.24, 35.56),
    "C6": (152.4, 35.56),
    "D1": (106.68, 55.88),
    "R4": (116.84, 55.88),
    "D2": (106.68, 116.84),
    "R5": (116.84, 116.84),
    # Isolation barrier, left to right.
    "R6": (170.18, 66.04),
    "R7": (170.18, 104.14),
    "U3": (200.66, 85.09),
    # Isolated power and output interface, left to right.
    "PS1": (187.96, 30.48),
    "C7": (165.1, 50.8),
    "C8": (205.74, 50.8),
    "U4": (228.6, 30.48),
    "C9": (246.38, 50.8),
    "C10": (256.54, 50.8),
    "JP1": (260.35, 55.88),
    "J2": (265.43, 85.09),
}

POWER_FLAGS = {
    "PWR_5V_USB": (80.01, 20.32),
    "GND": (134.62, 190.5),
}

PIN_STUB_LENGTH_MM = 7.62


def load_design() -> dict:
    with (PROJECT_ROOT / "design_intent.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def add_components(schematic, design: dict) -> None:
    for reference, component in design["components"].items():
        if reference not in POSITIONS:
            raise KeyError(f"Missing schematic position for {reference}")

        schematic.components.add(
            lib_id=component["symbol"],
            reference=reference,
            value=str(component["value"]),
            position=snap_point(*POSITIONS[reference], grid_mm=GRID_MM),
            footprint=component["footprint"],
        )


def add_power_flags(schematic) -> None:
    for index, (net_name, position) in enumerate(POWER_FLAGS.items(), start=1):
        reference = f"#FLG{index:02d}"
        schematic.components.add(
            lib_id="power:PWR_FLAG",
            reference=reference,
            value="PWR_FLAG",
            position=position,
        )
        add_pin_wire_and_label(schematic, net_name, reference, "1")


def pin_outward_delta(rotation: float, length: float) -> tuple[float, float]:
    """Return an outward stub vector in schematic coordinates."""
    outward_angle = (rotation + 180.0) % 360.0
    radians = math.radians(outward_angle)
    return (length * math.cos(radians), -length * math.sin(radians))


def add_pin_wire_and_label(
    schematic,
    net_name: str,
    reference: str,
    pin_number: str,
) -> None:
    component = schematic.components.get(reference)
    if component is None:
        raise ValueError(f"Cannot find component {reference}")

    pin_info = get_component_pin_info(component, pin_number)
    if pin_info is None:
        raise ValueError(f"Cannot find pin {reference}.{pin_number}")

    pin_position, pin_rotation = pin_info
    dx, dy = pin_outward_delta(pin_rotation, PIN_STUB_LENGTH_MM)
    label_position = snap_point(
        pin_position.x + dx,
        pin_position.y + dy,
        grid_mm=GRID_MM,
    )

    schematic.wires.add(start=pin_position, end=label_position)
    schematic.add_label(
        net_name,
        position=label_position,
        rotation=(pin_rotation + 180.0) % 360.0,
    )


def add_net_labels(schematic, design: dict) -> None:
    for net_name, net in design["nets"].items():
        for connection in net["connections"]:
            reference, pin = connection.split(".", 1)
            add_pin_wire_and_label(schematic, net_name, reference, pin)


def add_no_connects(schematic, design: dict) -> None:
    for connection in design.get("no_connect", []):
        reference, pin = connection.split(".", 1)
        position = schematic.get_component_pin_position(reference, pin)
        if position is None:
            raise ValueError(f"Cannot find no-connect pin {connection}")
        schematic.no_connects.add(position)


def main() -> None:
    HARDWARE_DIR.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / ".pyhome").mkdir(parents=True, exist_ok=True)

    design = load_design()
    schematic = ksa.create_schematic("USB_UART_Bridge")
    schematic.set_paper_size("A4")

    add_components(schematic, design)
    add_power_flags(schematic)
    add_net_labels(schematic, design)
    add_no_connects(schematic, design)

    assert_schematic_on_grid(schematic)

    issues = schematic.validate()
    errors = [issue for issue in issues if issue.level.value in ("error", "critical")]
    if errors:
        for issue in errors:
            print(issue)
        raise SystemExit("Schematic validation failed")

    schematic.save(SCHEMATIC_PATH)
    print(f"Generated: {SCHEMATIC_PATH}")
    print(f"Components: {len(schematic.components)}")
    print(f"Wires: {len(schematic.wires)}")
    print(f"Labels: {len(schematic.labels)}")
    print(f"No-connects: {len(schematic.no_connects)}")


if __name__ == "__main__":
    main()
