from __future__ import annotations

import argparse
import os
from pathlib import Path
import statistics
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_PYTHON = PROJECT_ROOT / "tools" / "python"
os.environ["USERPROFILE"] = str(PROJECT_ROOT / ".pyhome")
os.environ["HOME"] = str(PROJECT_ROOT / ".pyhome")
os.environ.setdefault("KICAD_SYMBOL_DIR", r"D:\KiCad10.0\share\kicad\symbols")
sys.path.insert(0, str(TOOLS_PYTHON))

import kicad_sch_api as ksa


SHEET_FILES = (
    "USB_UART_Bridge.kicad_sch",
    "Power.kicad_sch",
    "Communicate.kicad_sch",
)


def point_dict(point) -> dict[str, float]:
    return {"x": round(point.x, 4), "y": round(point.y, 4)}


def point_tuple(point) -> tuple[float, float]:
    return (round(point.x, 4), round(point.y, 4))


def text_position(item) -> tuple[float, float]:
    position = item.get("position", {})
    return (round(position.get("x", 0.0), 4), round(position.get("y", 0.0), 4))


def segment_dicts(schematic) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    segments = []
    for wire in schematic.wires:
        points = [point_tuple(point) for point in wire.points]
        for start, end in zip(points, points[1:]):
            segments.append(tuple(sorted((start, end))))
    return segments


def nearest_text_deltas(reference_items, candidate_items):
    unclaimed = list(reference_items)
    deltas = []
    for text, candidate_position in sorted(candidate_items, key=lambda item: item[0]):
        if not unclaimed:
            deltas.append((text, None, candidate_position))
            continue
        index = min(
            range(len(unclaimed)),
            key=lambda item_index: (
                abs(unclaimed[item_index][1][0] - candidate_position[0])
                + abs(unclaimed[item_index][1][1] - candidate_position[1])
            ),
        )
        reference_text, reference_position = unclaimed.pop(index)
        if text != reference_text:
            deltas.append((text, None, candidate_position))
            continue
        delta_x = round(candidate_position[0] - reference_position[0], 4)
        delta_y = round(candidate_position[1] - reference_position[1], 4)
        if delta_x or delta_y:
            deltas.append((text, (delta_x, delta_y), candidate_position))
    for text, position in unclaimed:
        deltas.append((text, None, position))
    return deltas


def print_component_diff(sheet_name: str, reference, candidate) -> None:
    reference_components = {
        component.reference: component for component in reference.components
    }
    candidate_components = {
        component.reference: component for component in candidate.components
    }
    keys = sorted(set(reference_components) | set(candidate_components))
    for key in keys:
        old = reference_components.get(key)
        new = candidate_components.get(key)
        if old is None:
            print(f"{sheet_name}: component {key} added at {point_dict(new.position)}")
            continue
        if new is None:
            print(f"{sheet_name}: component {key} removed")
            continue
        old_position = point_tuple(old.position)
        new_position = point_tuple(new.position)
        delta = (
            round(new_position[0] - old_position[0], 4),
            round(new_position[1] - old_position[1], 4),
        )
        if (
            delta != (0.0, 0.0)
            or round(old.rotation, 4) != round(new.rotation, 4)
            or old.value != new.value
            or old.footprint != new.footprint
        ):
            print(
                f"{sheet_name}: {key} delta={delta}, "
                f"rotation={old.rotation:g}->{new.rotation:g}, "
                f"value={old.value!r}->{new.value!r}, "
                f"footprint={old.footprint!r}->{new.footprint!r}"
            )


def print_label_diff(sheet_name: str, reference, candidate) -> None:
    reference_labels = [
        (label.text, point_tuple(label.position))
        for label in list(reference.labels) + list(reference.hierarchical_labels)
    ]
    candidate_labels = [
        (label.text, point_tuple(label.position))
        for label in list(candidate.labels) + list(candidate.hierarchical_labels)
    ]
    for text, delta, position in nearest_text_deltas(
        reference_labels,
        candidate_labels,
    ):
        if delta is None:
            print(
                f"{sheet_name}: label {text!r} count/position did not match "
                f"at {position}"
            )
        else:
            print(
                f"{sheet_name}: label {text!r} moved by {delta}, now {position}"
            )


def print_text_diff(sheet_name: str, reference, candidate) -> None:
    reference_texts = [
        (item.get("text", ""), text_position(item))
        for item in reference._data.get("texts", [])
    ]
    candidate_texts = [
        (item.get("text", ""), text_position(item))
        for item in candidate._data.get("texts", [])
    ]
    for text, delta, position in nearest_text_deltas(reference_texts, candidate_texts):
        if delta is None:
            print(
                f"{sheet_name}: annotation {text!r} count/position did not match "
                f"at {position}"
            )
        else:
            print(
                f"{sheet_name}: annotation {text!r} moved by {delta}, now {position}"
            )


def print_text_box_diff(sheet_name: str, reference, candidate) -> None:
    old_boxes = {
        item.get("text", ""): item for item in reference._data.get("text_boxes", [])
    }
    new_boxes = {
        item.get("text", ""): item for item in candidate._data.get("text_boxes", [])
    }
    for text in sorted(set(old_boxes) | set(new_boxes)):
        old = old_boxes.get(text)
        new = new_boxes.get(text)
        if old is None:
            print(f"{sheet_name}: text box {text.splitlines()[0]!r} added")
            continue
        if new is None:
            print(f"{sheet_name}: text box {text.splitlines()[0]!r} removed")
            continue
        old_position = text_position(old)
        new_position = text_position(new)
        old_size = old.get("size", {})
        new_size = new.get("size", {})
        delta = (
            round(new_position[0] - old_position[0], 4),
            round(new_position[1] - old_position[1], 4),
        )
        size_delta = (
            round(new_size.get("width", 0.0) - old_size.get("width", 0.0), 4),
            round(new_size.get("height", 0.0) - old_size.get("height", 0.0), 4),
        )
        if delta != (0.0, 0.0) or size_delta != (0.0, 0.0):
            print(
                f"{sheet_name}: text box {text.splitlines()[0]!r} "
                f"position delta={delta}, size delta={size_delta}"
            )


def print_sheet_diff(sheet_name: str, reference, candidate) -> None:
    old_sheets = {
        sheet.get("name", "?"): sheet for sheet in reference._data.get("sheets", [])
    }
    new_sheets = {
        sheet.get("name", "?"): sheet for sheet in candidate._data.get("sheets", [])
    }
    for name in sorted(set(old_sheets) | set(new_sheets)):
        old = old_sheets.get(name)
        new = new_sheets.get(name)
        if old is None:
            print(f"{sheet_name}: child sheet {name!r} added")
            continue
        if new is None:
            print(f"{sheet_name}: child sheet {name!r} removed")
            continue
        old_position = old.get("position", {})
        new_position = new.get("position", {})
        old_size = old.get("size", {})
        new_size = new.get("size", {})
        delta = (
            round(new_position.get("x", 0.0) - old_position.get("x", 0.0), 4),
            round(new_position.get("y", 0.0) - old_position.get("y", 0.0), 4),
        )
        size_delta = (
            round(new_size.get("width", 0.0) - old_size.get("width", 0.0), 4),
            round(new_size.get("height", 0.0) - old_size.get("height", 0.0), 4),
        )
        if delta != (0.0, 0.0) or size_delta != (0.0, 0.0):
            print(
                f"{sheet_name}: child sheet {name!r} "
                f"position delta={delta}, size delta={size_delta}"
            )


def print_wire_diff(sheet_name: str, reference, candidate) -> None:
    old_segments = segment_dicts(reference)
    new_segments = segment_dicts(candidate)
    old_set = set(old_segments)
    new_set = set(new_segments)
    removed = sorted(old_set - new_set)
    added = sorted(new_set - old_set)
    print(
        f"{sheet_name}: wires {len(old_segments)}->{len(new_segments)}, "
        f"segments removed={len(removed)}, added={len(added)}"
    )
    for start, end in removed[:20]:
        print(f"  removed {start}->{end}")
    for start, end in added[:20]:
        print(f"  added   {start}->{end}")


def style_metrics(schematic) -> dict[str, float | int]:
    components = [
        component
        for component in schematic.components
        if not component.reference.startswith(("#PWR", "#FLG"))
    ]
    positions = [point_tuple(component.position) for component in components]
    wire_segments = segment_dicts(schematic)
    wire_lengths = [
        abs(end[0] - start[0]) + abs(end[1] - start[1])
        for start, end in wire_segments
    ]
    labels = [
        point_tuple(label.position)
        for label in list(schematic.labels) + list(schematic.hierarchical_labels)
    ]
    text_boxes = schematic._data.get("text_boxes", [])

    nearest_component_distances = []
    for index, (x, y) in enumerate(positions):
        distances = [
            abs(x - other_x) + abs(y - other_y)
            for other_index, (other_x, other_y) in enumerate(positions)
            if other_index != index
        ]
        if distances:
            nearest_component_distances.append(min(distances))

    nearest_label_distances = []
    for index, (x, y) in enumerate(labels):
        distances = [
            abs(x - other_x) + abs(y - other_y)
            for other_index, (other_x, other_y) in enumerate(labels)
            if other_index != index
        ]
        if distances:
            nearest_label_distances.append(min(distances))

    text_box_area = 0.0
    for text_box in text_boxes:
        size = text_box.get("size", {})
        text_box_area += size.get("width", 0.0) * size.get("height", 0.0)

    return {
        "components": len(components),
        "component_bbox": (
            (
                round(min(point[0] for point in positions), 2),
                round(min(point[1] for point in positions), 2),
            ),
            (
                round(max(point[0] for point in positions), 2),
                round(max(point[1] for point in positions), 2),
            ),
        )
        if positions
        else None,
        "component_center": (
            round(statistics.fmean(point[0] for point in positions), 2),
            round(statistics.fmean(point[1] for point in positions), 2),
        )
        if positions
        else None,
        "mean_nearest_component_distance": round(
            statistics.fmean(nearest_component_distances), 2
        )
        if nearest_component_distances
        else 0.0,
        "wire_segments": len(wire_segments),
        "wire_length": round(sum(wire_lengths), 2),
        "mean_wire_segment": round(statistics.fmean(wire_lengths), 2)
        if wire_lengths
        else 0.0,
        "labels": len(labels),
        "mean_nearest_label_distance": round(
            statistics.fmean(nearest_label_distances), 2
        )
        if nearest_label_distances
        else 0.0,
        "text_boxes": len(text_boxes),
        "text_box_area": round(text_box_area, 2),
    }


def print_style_metrics(sheet_name: str, reference, candidate) -> None:
    print(f"{sheet_name}: style metrics")
    print(f"  reference={style_metrics(reference)}")
    print(f"  manual   ={style_metrics(candidate)}")


def compare_layout(reference_dir: Path, candidate_dir: Path) -> None:
    for filename in SHEET_FILES:
        reference_path = reference_dir / filename
        candidate_path = candidate_dir / filename
        if not reference_path.exists() or not candidate_path.exists():
            print(f"{filename}: missing reference or candidate file")
            continue
        reference = ksa.load_schematic(reference_path)
        candidate = ksa.load_schematic(candidate_path)
        print(f"===== {filename} =====")
        print_style_metrics(filename, reference, candidate)
        print_component_diff(filename, reference, candidate)
        print_label_diff(filename, reference, candidate)
        print_text_diff(filename, reference, candidate)
        print_text_box_diff(filename, reference, candidate)
        print_sheet_diff(filename, reference, candidate)
        print_wire_diff(filename, reference, candidate)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference_dir", type=Path)
    parser.add_argument("candidate_dir", type=Path)
    args = parser.parse_args()
    compare_layout(args.reference_dir, args.candidate_dir)


if __name__ == "__main__":
    main()
