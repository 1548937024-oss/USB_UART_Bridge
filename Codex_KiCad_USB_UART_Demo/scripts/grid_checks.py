from __future__ import annotations

import math
import re


GRID_MM = 1.27


def is_on_grid(value: float, grid_mm: float = GRID_MM) -> bool:
    return math.isclose(value / grid_mm, round(value / grid_mm), abs_tol=1e-6)


def snap_to_grid(value: float, grid_mm: float = GRID_MM) -> float:
    return round(value / grid_mm) * grid_mm


def snap_point(x: float, y: float, grid_mm: float = GRID_MM) -> tuple[float, float]:
    return (snap_to_grid(x, grid_mm), snap_to_grid(y, grid_mm))


def _point_key(point) -> tuple[float, float]:
    return (round(point.x, 4), round(point.y, 4))


def _orientation(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _point_on_segment(a, b, c) -> bool:
    return (
        min(a[0], b[0]) - 1e-6 <= c[0] <= max(a[0], b[0]) + 1e-6
        and min(a[1], b[1]) - 1e-6 <= c[1] <= max(a[1], b[1]) + 1e-6
    )


def _segment_intersection(a, b, c, d):
    o1 = _orientation(a, b, c)
    o2 = _orientation(a, b, d)
    o3 = _orientation(c, d, a)
    o4 = _orientation(c, d, b)

    if abs(o1) < 1e-6 and _point_on_segment(a, b, c):
        return c
    if abs(o2) < 1e-6 and _point_on_segment(a, b, d):
        return d
    if abs(o3) < 1e-6 and _point_on_segment(c, d, a):
        return a
    if abs(o4) < 1e-6 and _point_on_segment(c, d, b):
        return b

    if o1 * o2 < 0 and o3 * o4 < 0:
        denominator = (a[0] - b[0]) * (c[1] - d[1]) - (a[1] - b[1]) * (c[0] - d[0])
        if abs(denominator) < 1e-12:
            return None
        x = (
            (a[0] * b[1] - a[1] * b[0]) * (c[0] - d[0])
            - (a[0] - b[0]) * (c[0] * d[1] - c[1] * d[0])
        ) / denominator
        y = (
            (a[0] * b[1] - a[1] * b[0]) * (c[1] - d[1])
            - (a[1] - b[1]) * (c[0] * d[1] - c[1] * d[0])
        ) / denominator
        return (round(x, 4), round(y, 4))

    return None


def find_off_grid_items(schematic) -> list[str]:
    from kicad_sch_api.core.pin_utils import list_component_pins

    issues: list[str] = []

    for component in schematic.components:
        if not is_on_grid(component.position.x) or not is_on_grid(component.position.y):
            issues.append(
                f"component {component.reference} origin "
                f"({component.position.x:.6f}, {component.position.y:.6f})"
            )

        for pin_number, position in list_component_pins(component):
            if not is_on_grid(position.x) or not is_on_grid(position.y):
                issues.append(
                    f"pin {component.reference}.{pin_number} "
                    f"({position.x:.6f}, {position.y:.6f})"
                )

    for wire in schematic.wires:
        for index, point in enumerate(wire.points):
            if not is_on_grid(point.x) or not is_on_grid(point.y):
                issues.append(
                    f"wire {wire.uuid} point {index} "
                    f"({point.x:.6f}, {point.y:.6f})"
                )

    for label in schematic.labels:
        if not is_on_grid(label.position.x) or not is_on_grid(label.position.y):
            issues.append(
                f"label {label.text} "
                f"({label.position.x:.6f}, {label.position.y:.6f})"
            )

    for label in schematic.hierarchical_labels:
        if not is_on_grid(label.position.x) or not is_on_grid(label.position.y):
            issues.append(
                f"hierarchical label {label.text} "
                f"({label.position.x:.6f}, {label.position.y:.6f})"
            )

    for no_connect in schematic.no_connects:
        if (
            not is_on_grid(no_connect.position.x)
            or not is_on_grid(no_connect.position.y)
        ):
            issues.append(
                f"no_connect {no_connect.uuid} "
                f"({no_connect.position.x:.6f}, {no_connect.position.y:.6f})"
            )

    for junction in schematic.junctions:
        if (
            not is_on_grid(junction.position.x)
            or not is_on_grid(junction.position.y)
        ):
            issues.append(
                f"junction {junction.uuid} "
                f"({junction.position.x:.6f}, {junction.position.y:.6f})"
            )

    for sheet in schematic._data.get("sheets", []):
        position = sheet.get("position", {})
        x = position.get("x")
        y = position.get("y")
        if x is not None and y is not None and (not is_on_grid(x) or not is_on_grid(y)):
            issues.append(f"sheet {sheet.get('name', '?')} origin ({x:.6f}, {y:.6f})")

        for pin in sheet.get("pins", []):
            pin_position = pin.get("position", {})
            pin_x = pin_position.get("x")
            pin_y = pin_position.get("y")
            if (
                pin_x is not None
                and pin_y is not None
                and (not is_on_grid(pin_x) or not is_on_grid(pin_y))
            ):
                issues.append(
                    f"sheet pin {sheet.get('name', '?')}.{pin.get('name', '?')} "
                    f"({pin_x:.6f}, {pin_y:.6f})"
                )

    return issues


def find_missing_footprints(schematic) -> list[str]:
    issues: list[str] = []
    for component in schematic.components:
        if component.reference.startswith("#"):
            continue
        if not component.footprint:
            issues.append(f"component {component.reference} has no footprint")
    return issues


def _labels(schematic):
    return list(schematic.labels) + list(schematic.hierarchical_labels)


def _point_on_wire(point, start, end) -> bool:
    return (
        abs(_orientation(start, end, point)) < 1e-6
        and _point_on_segment(start, end, point)
    )


def find_labels_off_wires(schematic) -> list[str]:
    wire_segments = [
        ((wire.points[0].x, wire.points[0].y), (wire.points[-1].x, wire.points[-1].y))
        for wire in schematic.wires
        if len(wire.points) >= 2
    ]
    issues: list[str] = []
    for label in _labels(schematic):
        point = (label.position.x, label.position.y)
        if not any(_point_on_wire(point, start, end) for start, end in wire_segments):
            issues.append(f"label {label.text} is not placed on a wire")
    return issues


def find_invalid_net_names(schematic) -> list[str]:
    issues: list[str] = []
    for label in _labels(schematic):
        text = label.text
        if re.fullmatch(r"NET\d+", text, flags=re.IGNORECASE) or re.fullmatch(
            r"[A-Za-z]", text
        ) or text.upper() == "DATA":
            issues.append(f"invalid or ambiguous net name: {text}")
    return issues


def find_unexpected_global_labels(schematic) -> list[str]:
    return [
        f"unexpected global label: {label.get('text', '?')}"
        for label in schematic._data.get("global_label", [])
    ]


def find_invalid_wire_angles(schematic) -> list[str]:
    issues: list[str] = []
    for wire in schematic.wires:
        if len(wire.points) < 2:
            continue
        start = wire.points[0]
        end = wire.points[-1]
        delta_x = abs(end.x - start.x)
        delta_y = abs(end.y - start.y)
        if delta_x < 1e-6 or delta_y < 1e-6:
            continue
        issues.append(
            f"wire {wire.uuid} uses a diagonal or non-orthogonal angle"
        )
    return issues


def find_out_of_bounds_items(
    schematic,
    min_x: float = 20.0,
    max_x: float = 287.0,
    min_y: float = 10.0,
    max_y: float = 200.0,
) -> list[str]:
    from kicad_sch_api.core.component_bounds import get_component_bounding_box

    issues: list[str] = []
    for component in schematic.components:
        if component.reference.startswith(("#PWR", "#FLG")):
            continue
        box = get_component_bounding_box(component, include_properties=False)
        if (
            box.min_x < min_x
            or box.max_x > max_x
            or box.min_y < min_y
            or box.max_y > max_y
        ):
            issues.append(
                f"component {component.reference} exceeds drawing border: "
                f"({box.min_x:.2f}, {box.min_y:.2f})-"
                f"({box.max_x:.2f}, {box.max_y:.2f})"
            )

    for wire in schematic.wires:
        for point in wire.points:
            if not (min_x <= point.x <= max_x and min_y <= point.y <= max_y):
                issues.append(
                    f"wire {wire.uuid} point ({point.x:.2f}, {point.y:.2f}) "
                    "exceeds drawing border"
                )

    for text_box in schematic._data.get("text_boxes", []):
        position = text_box.get("position", {})
        size = text_box.get("size", {})
        x = position.get("x")
        y = position.get("y")
        width = size.get("width")
        height = size.get("height")
        if None in (x, y, width, height):
            continue
        if x < min_x or y < min_y or x + width > max_x or y + height > max_y:
            issues.append(
                f"text box '{text_box.get('text', '?').splitlines()[0]}' "
                "exceeds drawing border"
            )

    return issues


def find_close_text_anchors(schematic) -> list[str]:
    items: list[tuple[str, float, float]] = []
    for label in schematic.labels:
        items.append((f"label {label.text}", label.position.x, label.position.y))
    for label in schematic.hierarchical_labels:
        items.append(
            (f"hierarchical label {label.text}", label.position.x, label.position.y)
        )
    for text in schematic._data.get("texts", []):
        position = text.get("position", {})
        items.append(
            (
                f"text {text.get('text', '?').splitlines()[0]}",
                position.get("x", 0.0),
                position.get("y", 0.0),
            )
        )

    issues: list[str] = []
    for index, (name_a, x_a, y_a) in enumerate(items):
        for name_b, x_b, y_b in items[index + 1 :]:
            if abs(x_a - x_b) + abs(y_a - y_b) < 3.81:
                issues.append(
                    f"text anchors are too close: '{name_a}' and '{name_b}'"
                )
    return issues


def find_overlapping_text_boxes(schematic) -> list[str]:
    boxes: list[tuple[str, float, float, float, float]] = []
    for text_box in schematic._data.get("text_boxes", []):
        position = text_box.get("position", {})
        size = text_box.get("size", {})
        x = position.get("x")
        y = position.get("y")
        width = size.get("width")
        height = size.get("height")
        if None in (x, y, width, height):
            continue
        boxes.append(
            (
                f"text box {text_box.get('text', '?').splitlines()[0]}",
                x,
                y,
                x + width,
                y + height,
            )
        )

    issues: list[str] = []
    for index, (name_a, min_x_a, min_y_a, max_x_a, max_y_a) in enumerate(boxes):
        for name_b, min_x_b, min_y_b, max_x_b, max_y_b in boxes[index + 1 :]:
            if not (
                max_x_a <= min_x_b
                or min_x_a >= max_x_b
                or max_y_a <= min_y_b
                or min_y_a >= max_y_b
            ):
                issues.append(f"text boxes overlap: '{name_a}' and '{name_b}'")
    return issues


def find_different_net_intersections(schematic) -> list[str]:
    from kicad_sch_api.core.pin_utils import list_component_pins

    wire_segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for wire in schematic.wires:
        if len(wire.points) < 2:
            continue
        wire_segments.append(
            (_point_key(wire.points[0]), _point_key(wire.points[-1]))
        )

    associated_nets: list[tuple[tuple[float, float], str]] = []
    for label in schematic.labels:
        associated_nets.append((_point_key(label.position), label.text))

    for label in schematic.hierarchical_labels:
        associated_nets.append((_point_key(label.position), label.text))

    for component in schematic.components:
        if not component.reference.startswith("#PWR"):
            continue
        for _, pin_position in list_component_pins(component):
            associated_nets.append(
                (_point_key(pin_position), component.value)
            )

    points = {
        point
        for segment in wire_segments
        for point in segment
    } | {point for point, _ in associated_nets}
    parent = {point: point for point in points}

    def find(point: tuple[float, float]) -> tuple[float, float]:
        while parent[point] != point:
            parent[point] = parent[parent[point]]
            point = parent[point]
        return point

    def union(a: tuple[float, float], b: tuple[float, float]) -> None:
        root_a = find(a)
        root_b = find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    for start, end in wire_segments:
        union(start, end)
        for point, _ in associated_nets:
            if (
                abs(_orientation(start, end, point)) < 1e-6
                and _point_on_segment(start, end, point)
            ):
                union(start, point)

    component_nets: dict[tuple[float, float], set[str]] = {}
    for point, net_name in associated_nets:
        component_nets.setdefault(find(point), set()).add(net_name)

    wires: list[tuple[tuple[float, float], tuple[float, float], set[str]]] = []
    for start, end in wire_segments:
        wires.append((start, end, component_nets.get(find(start), set())))

    issues: list[str] = []
    for index, (start_a, end_a, nets_a) in enumerate(wires):
        for start_b, end_b, nets_b in wires[index + 1 :]:
            if not nets_a or not nets_b or nets_a == nets_b:
                continue
            intersection = _segment_intersection(
                start_a,
                end_a,
                start_b,
                end_b,
            )
            if intersection is not None:
                issues.append(
                    "different-net wires intersect at "
                    f"{intersection}: {sorted(nets_a)} / {sorted(nets_b)}"
                )

    return issues


def assert_schematic_on_grid(schematic) -> None:
    issues = find_off_grid_items(schematic)
    issues.extend(find_missing_footprints(schematic))
    issues.extend(find_labels_off_wires(schematic))
    issues.extend(find_invalid_net_names(schematic))
    issues.extend(find_unexpected_global_labels(schematic))
    issues.extend(find_invalid_wire_angles(schematic))
    issues.extend(find_out_of_bounds_items(schematic))
    issues.extend(find_close_text_anchors(schematic))
    issues.extend(find_overlapping_text_boxes(schematic))
    issues.extend(find_different_net_intersections(schematic))
    if issues:
        details = "\n".join(f"- {issue}" for issue in issues)
        raise ValueError(
            f"Schematic validation failed at the {GRID_MM} mm grid:\n{details}"
        )
