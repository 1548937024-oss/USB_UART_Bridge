from pathlib import Path
import json
import math
import os
import re
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_PYTHON = PROJECT_ROOT / "tools" / "python"
HARDWARE_DIR = PROJECT_ROOT / "hardware" / "USB_UART_Bridge"
PROJECT_NAME = "USB_UART_Bridge"
TOP_PATH = HARDWARE_DIR / f"{PROJECT_NAME}.kicad_sch"
POWER_PATH = HARDWARE_DIR / "Power.kicad_sch"
COMMUNICATE_PATH = HARDWARE_DIR / "Communicate.kicad_sch"
PROJECT_PATH = HARDWARE_DIR / f"{PROJECT_NAME}.kicad_pro"
DRAWING_SHEET_NAME = "AD_Style_A4.kicad_wks"
KICAD_CLI = Path(r"D:\KiCad10.0\bin\kicad-cli.exe")

os.environ.setdefault("KICAD_SYMBOL_DIR", r"D:\KiCad10.0\share\kicad\symbols")
os.environ["USERPROFILE"] = str(PROJECT_ROOT / ".pyhome")
os.environ["HOME"] = str(PROJECT_ROOT / ".pyhome")

sys.path.insert(0, str(TOOLS_PYTHON))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import yaml
import kicad_sch_api as ksa
from kicad_sch_api.core.pin_utils import get_component_pin_info

from grid_checks import GRID_MM, assert_schematic_on_grid, snap_point


PIN_STUB_LENGTH_MM = 3.81
LABEL_STUB_LENGTH_MM = 7.62
SINGLETON_LABEL_OFFSET_MM = LABEL_STUB_LENGTH_MM
MAX_ROUTE_SPAN_MM = 25.4
DIRECT_POWER_PINS = {"C7.1", "C8.1", "C9.1", "C10.1"}

POWER_NETS = {
    "PWR_5V_RAW",
    "PWR_5V_USB",
    "PWR_3V3_USB",
    "PWR_5V_ISO",
    "PWR_3V3_ISO",
    "PWR_VOUT_ISO",
    "GND",
    "ISO_GND",
}

POWER_SYMBOLS = {
    "PWR_5V_RAW": "power:+5V",
    "PWR_5V_USB": "power:+5V",
    "PWR_3V3_USB": "power:+3V3",
    "PWR_5V_ISO": "power:+5V",
    "PWR_3V3_ISO": "power:+3V3",
    "PWR_VOUT_ISO": "power:+5V",
    "GND": "power:GND",
    "ISO_GND": "power:GND",
}

POWER_FLAG_NETS = {"PWR_5V_RAW", "PWR_5V_USB", "PWR_VOUT_ISO", "GND"}

CROSS_SHEET_SIGNALS = {
    "USB_DP": "bidirectional",
    "USB_DM": "bidirectional",
    "UART_TX_ISO_OUT": "output",
    "UART_RX_ISO_IN": "input",
}

NET_ROUTING_PRIORITY = {
    "LED_ACT_DRIVE": 0,
    "LED_ACT_K": 0,
    "LED_PWR_K": 0,
    "USB_DP": 0,
    "USB_DM": 0,
    "UART_TX_BRIDGE": 1,
    "UART_TX_ISO_IN": 1,
    "UART_TX_ISO_OUT": 1,
    "UART_RX_BRIDGE": 2,
    "UART_RX_ISO_OUT": 2,
    "UART_RX_ISO_IN": 2,
    "USB_CC1": 3,
    "USB_CC2": 3,
}

TOP_COMPONENTS = {"J1", "U2", "R1", "R2", "J2", "JP1", "TP3", "TP4"}
POWER_COMPONENTS = {
    "F1",
    "C1",
    "PS1",
    "C7",
    "C8",
    "U4",
    "C9",
    "C10",
    "TP1",
    "TP2",
}
COMMUNICATE_COMPONENTS = {
    "U1",
    "C2",
    "C3",
    "C4",
    "C5",
    "C6",
    "C11",
    "C12",
    "D1",
    "R4",
    "D2",
    "R5",
    "R6",
    "R7",
    "U3",
}

# Coordinates are preserved from the last manually reviewed flat schematic.
POSITIONS = {
    "J1": (45.72, 127.0),
    "U2": (100.33, 127.0),
    "R1": (78.74, 116.84),
    "R2": (88.9, 124.46),
    "J2": (255.27, 81.28),
    "JP1": (248.92, 55.88),
    "TP3": (250.19, 64.77),
    "TP4": (250.19, 91.44),
    "F1": (45.72, 36.83),
    "C1": (63.5, 36.83),
    "PS1": (187.96, 30.48),
    "C7": (175.26, 17.78),
    "C8": (200.66, 17.78),
    "U4": (228.6, 30.48),
    "C9": (236.22, 19.05),
    "C10": (243.84, 19.05),
    "TP1": (80.01, 36.83),
    "TP2": (248.92, 38.1),
    "C11": (224.79, 72.39),
    "C12": (236.22, 72.39),
    "U1": (134.62, 85.09),
    "C2": (106.68, 57.15),
    "C3": (119.38, 57.15),
    "C4": (132.08, 57.15),
    "C5": (144.78, 57.15),
    "C6": (157.48, 57.15),
    "D1": (156.21, 86.36),
    "R4": (152.4, 80.01),
    "D2": (104.14, 116.84),
    "R5": (120.65, 116.84),
    "R6": (170.18, 80.01),
    "R7": (242.57, 86.36),
    "U3": (210.82, 83.82),
}

ROTATIONS = {
    "C7": 180,
    "C8": 180,
    "C9": 180,
    "C10": 180,
    "C11": 180,
    "C12": 180,
    "D2": 180,
    "D1": 90,
    "R4": 270,
    "R5": 270,
    "R6": 270,
    "R7": 90,
}


class ReferenceAllocator:
    def __init__(self) -> None:
        self.power_index = 1
        self.flag_index = 1

    def next_power(self) -> str:
        reference = f"#PWR{self.power_index:03d}"
        self.power_index += 1
        return reference

    def next_flag(self) -> str:
        reference = f"#FLG{self.flag_index:03d}"
        self.flag_index += 1
        return reference


def load_design() -> dict:
    with (PROJECT_ROOT / "design_intent.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def create_schematic(name: str):
    schematic = ksa.create_schematic(name)
    schematic.set_paper_size("A4")
    return schematic


def pin_stub(
    schematic,
    reference: str,
    pin_number: str,
    length_mm: float = PIN_STUB_LENGTH_MM,
):
    component = schematic.components.get(reference)
    if component is None:
        raise ValueError(f"Cannot find component {reference}")

    pin_info = get_component_pin_info(component, pin_number)
    if pin_info is None:
        raise ValueError(f"Cannot find pin {reference}.{pin_number}")

    pin_position, pin_rotation = pin_info
    delta_x = pin_position.x - component.position.x
    delta_y = pin_position.y - component.position.y
    if abs(delta_x) >= abs(delta_y) and abs(delta_x) > 1e-6:
        outward_angle = 0.0 if delta_x > 0 else 180.0
    elif abs(delta_y) > 1e-6:
        outward_angle = 90.0 if delta_y < 0 else 270.0
    else:
        outward_angle = (pin_rotation + 180.0) % 360.0
    radians = math.radians(outward_angle)
    endpoint = snap_point(
        pin_position.x + length_mm * math.cos(radians),
        pin_position.y - length_mm * math.sin(radians),
        grid_mm=GRID_MM,
    )
    schematic.wires.add(start=pin_position, end=endpoint)
    return endpoint, outward_angle


def component_pin_position(schematic, reference: str, pin_number: str):
    component = schematic.components.get(reference)
    if component is None:
        raise ValueError(f"Cannot find component {reference}")
    pin_info = get_component_pin_info(component, pin_number)
    if pin_info is None:
        raise ValueError(f"Cannot find pin {reference}.{pin_number}")
    return snap_point(pin_info[0].x, pin_info[0].y, grid_mm=GRID_MM)


def register_signal_node(
    nodes_by_net: dict[str, list[tuple[float, float]]],
    net_name: str,
    point: tuple[float, float],
) -> None:
    point = snap_point(*point, grid_mm=GRID_MM)
    nodes_by_net.setdefault(net_name, [])
    if point not in nodes_by_net[net_name]:
        nodes_by_net[net_name].append(point)


def _segment_key(a: tuple[float, float], b: tuple[float, float]):
    return (a, b) if a <= b else (b, a)


def _orientation(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _point_on_segment(a, b, c) -> bool:
    return (
        min(a[0], b[0]) - 1e-6 <= c[0] <= max(a[0], b[0]) + 1e-6
        and min(a[1], b[1]) - 1e-6 <= c[1] <= max(a[1], b[1]) + 1e-6
    )


def _point_on_wire(point, start, end) -> bool:
    return (
        abs(_orientation(start, end, point)) < 1e-6
        and _point_on_segment(start, end, point)
    )


def segments_intersect(a, b, c, d) -> bool:
    o1 = _orientation(a, b, c)
    o2 = _orientation(a, b, d)
    o3 = _orientation(c, d, a)
    o4 = _orientation(c, d, b)

    if abs(o1) < 1e-6 and _point_on_segment(a, b, c):
        return True
    if abs(o2) < 1e-6 and _point_on_segment(a, b, d):
        return True
    if abs(o3) < 1e-6 and _point_on_segment(c, d, a):
        return True
    if abs(o4) < 1e-6 and _point_on_segment(c, d, b):
        return True
    return o1 * o2 < 0 and o3 * o4 < 0


def _point_key(point: tuple[float, float]) -> tuple[float, float]:
    return (round(point[0], 4), round(point[1], 4))


def manhattan_paths(
    start: tuple[float, float],
    end: tuple[float, float],
) -> list[list[tuple[float, float]]]:
    if start[0] == end[0] or start[1] == end[1]:
        return [[start, end]]
    return [
        [start, (end[0], start[1]), end],
        [start, (start[0], end[1]), end],
    ]


def infer_existing_wire_nets(schematic) -> list[tuple[tuple, tuple, set[str]]]:
    net_points: dict[tuple[float, float], set[str]] = {}

    def register(point, net_name: str) -> None:
        key = (round(point.x, 4), round(point.y, 4))
        net_points.setdefault(key, set()).add(net_name)

    for label in schematic.labels:
        register(label.position, label.text)
    for label in schematic.hierarchical_labels:
        register(label.position, label.text)

    from kicad_sch_api.core.pin_utils import list_component_pins

    for component in schematic.components:
        if component.reference.startswith("#PWR"):
            for _, pin_position in list_component_pins(component):
                register(pin_position, component.value)

    segments: list[tuple[tuple, tuple, set[str]]] = []
    for wire in schematic.wires:
        if len(wire.points) < 2:
            continue
        start = (round(wire.points[0].x, 4), round(wire.points[0].y, 4))
        end = (round(wire.points[-1].x, 4), round(wire.points[-1].y, 4))
        nets = net_points.get(start, set()) | net_points.get(end, set())
        segments.append((start, end, nets))
    return segments


def _build_routing_clusters(
    nodes_by_net: dict[str, list[tuple[float, float]]],
) -> list[tuple[str, list[tuple[float, float]]]]:
    clusters: list[tuple[str, list[tuple[float, float]]]] = []
    for net_name, points in nodes_by_net.items():
        unique_points = list(dict.fromkeys(points))
        parent = list(range(len(unique_points)))

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(index_a: int, index_b: int) -> None:
            root_a = find(index_a)
            root_b = find(index_b)
            if root_a != root_b:
                parent[root_b] = root_a

        for i, (x_a, y_a) in enumerate(unique_points):
            for j in range(i + 1, len(unique_points)):
                x_b, y_b = unique_points[j]
                if abs(x_a - x_b) + abs(y_a - y_b) <= MAX_ROUTE_SPAN_MM:
                    union(i, j)

        grouped: dict[int, list[tuple[float, float]]] = {}
        for index, point in enumerate(unique_points):
            grouped.setdefault(find(index), []).append(point)
        for cluster_points in grouped.values():
            clusters.append((net_name, cluster_points))

    return sorted(
        clusters,
        key=lambda item: (
            NET_ROUTING_PRIORITY.get(item[0], 10),
            item[0],
            min(point[0] for point in item[1]),
            min(point[1] for point in item[1]),
        ),
    )


def route_signal_nets(
    schematic,
    nodes_by_net: dict[str, list[tuple[float, float]]],
) -> list[
    tuple[
        str,
        list[tuple[float, float]],
        list[tuple[tuple[float, float], tuple[float, float]]],
    ]
]:
    existing_segments = infer_existing_wire_nets(schematic)
    routed_segments = list(existing_segments)
    routed_clusters: list[
        tuple[
            str,
            list[tuple[float, float]],
            list[tuple[tuple[float, float], tuple[float, float]]],
        ]
    ] = []
    point_degree: dict[tuple[float, float], int] = {}
    endpoint_nets: dict[tuple[float, float], set[str]] = {}

    pin_nets: dict[tuple[float, float], set[str]] = {}
    for net_name, points in nodes_by_net.items():
        for point in points:
            pin_nets.setdefault(point, set()).add(net_name)

    for net_name, cluster_points in _build_routing_clusters(nodes_by_net):
        cluster_segments: list[
            tuple[tuple[float, float], tuple[float, float]]
        ] = []
        routed_clusters.append((net_name, cluster_points, cluster_segments))
        if len(cluster_points) < 2:
            continue

        # Prim's algorithm over Manhattan distance inside one local cluster.
        connected = {0}
        edges: list[tuple[int, int]] = []
        while len(connected) < len(cluster_points):
            best = None
            for i in connected:
                for j in range(len(cluster_points)):
                    if j in connected:
                        continue
                    distance = (
                        abs(cluster_points[i][0] - cluster_points[j][0])
                        + abs(cluster_points[i][1] - cluster_points[j][1])
                    )
                    candidate = (distance, i, j)
                    if best is None or candidate < best:
                        best = candidate
            if best is None:
                break
            _, i, j = best
            edges.append((i, j))
            connected.add(j)

        for i, j in edges:
            start = cluster_points[i]
            end = cluster_points[j]
            min_x = min(start[0], end[0])
            max_x = max(start[0], end[0])
            min_y = min(start[1], end[1])
            max_y = max(start[1], end[1])
            candidate_paths = manhattan_paths(start, end)

            offsets = [
                5.08,
                10.16,
                15.24,
                20.32,
                25.4,
                38.1,
                50.8,
                76.2,
                101.6,
            ]
            for offset in offsets:
                for channel_y in (min_y - offset, max_y + offset):
                    candidate_paths.append(
                        [start, (start[0], channel_y), (end[0], channel_y), end]
                    )
                for channel_x in (min_x - offset, max_x + offset):
                    candidate_paths.append(
                        [start, (channel_x, start[1]), (channel_x, end[1]), end]
                    )
                for channel_x in (min_x - offset, max_x + offset):
                    for channel_y in (min_y - offset, max_y + offset):
                        candidate_paths.append(
                            [
                                start,
                                (start[0], channel_y),
                                (channel_x, channel_y),
                                (channel_x, end[1]),
                                end,
                            ]
                        )

            scored_paths = []
            for path in candidate_paths:
                hard_conflicts = 0
                crossings = 0
                length = 0
                for p1, p2 in zip(path, path[1:]):
                    length += abs(p2[0] - p1[0]) + abs(p2[1] - p1[1])
                    for pin_point, pin_net_names in pin_nets.items():
                        if net_name in pin_net_names:
                            continue
                        if _point_on_segment(p1, p2, pin_point):
                            hard_conflicts += 1
                    for q1, q2, nets in routed_segments:
                        if net_name in nets:
                            continue
                        if segments_intersect(p1, p2, q1, q2):
                            hard_conflicts += 1
                            crossings += 1
                scored_paths.append(
                    (hard_conflicts, length, crossings, len(path), path)
                )

            valid_paths = [entry for entry in scored_paths if entry[0] == 0]
            if not valid_paths:
                best_conflict = min(scored_paths, key=lambda item: item[0])
                conflict_segments = []
                for p1, p2 in zip(best_conflict[4], best_conflict[4][1:]):
                    for pin_point, pin_net_names in pin_nets.items():
                        if net_name in pin_net_names:
                            continue
                        if _point_on_segment(p1, p2, pin_point):
                            conflict_segments.append(
                                (p1, p2, ["PIN"], pin_point, sorted(pin_net_names))
                            )
                    for q1, q2, nets in routed_segments:
                        if net_name in nets:
                            continue
                        if segments_intersect(p1, p2, q1, q2):
                            conflict_segments.append((p1, p2, sorted(nets), q1, q2))
                raise ValueError(
                    f"No short Manhattan route without electrical conflict "
                    f"for {net_name} from {start} to {end}; "
                    f"conflicts={conflict_segments[:5]}"
                )
            _, _, _, _, selected_path = min(
                valid_paths,
                key=lambda item: (item[1], item[2], item[3]),
            )
            for p1, p2 in zip(selected_path, selected_path[1:]):
                schematic.wires.add(start=p1, end=p2)
                routed_segments.append((p1, p2, {net_name}))
                if p1 != p2:
                    cluster_segments.append((p1, p2))
                for point in (p1, p2):
                    point_degree[point] = point_degree.get(point, 0) + 1
                    endpoint_nets.setdefault(point, set()).add(net_name)

    pin_points = {
        component_pin_position(schematic, component.reference, pin.number)
        for component in schematic.components
        for pin in component.pins
    }
    for point, degree in point_degree.items():
        if degree >= 3 and point not in pin_points:
            schematic.junctions.add(point)

    for point, nets in endpoint_nets.items():
        touched_midsection = False
        for q1, q2, segment_nets in routed_segments:
            if not (nets & segment_nets):
                continue
            if point == q1 or point == q2:
                continue
            if _point_on_segment(q1, q2, point):
                touched_midsection = True
                break
        if touched_midsection and schematic.junctions.get_at_position(point) is None:
            schematic.junctions.add(point)

    return routed_clusters


def _segment_grid_points(
    start: tuple[float, float],
    end: tuple[float, float],
) -> list[tuple[float, float]]:
    if start[0] == end[0]:
        step_count = int(round(abs(end[1] - start[1]) / GRID_MM))
        direction = 1 if end[1] > start[1] else -1
        return [
            snap_point(start[0], start[1] + direction * index * GRID_MM)
            for index in range(step_count + 1)
        ]

    if start[1] == end[1]:
        step_count = int(round(abs(end[0] - start[0]) / GRID_MM))
        direction = 1 if end[0] > start[0] else -1
        return [
            snap_point(start[0] + direction * index * GRID_MM, start[1])
            for index in range(step_count + 1)
        ]

    return [start, end]


def _label_rotation(
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    return 0.0 if start[1] == end[1] else 90.0


def _label_collision_count(
    position: tuple[float, float],
    rotation: float,
    existing_positions: list[tuple[float, float]],
) -> int:
    horizontal = rotation == 0.0
    half_width = 8.0 if horizontal else 2.0
    half_height = 2.0 if horizontal else 8.0
    collisions = 0
    for other_x, other_y in existing_positions:
        anchor_distance = abs(position[0] - other_x) + abs(position[1] - other_y)
        if anchor_distance < 5.08 or (
            abs(position[0] - other_x) < half_width * 2
            and abs(position[1] - other_y) < half_height * 2
        ):
            collisions += 1
    return collisions


def add_routed_net_labels(
    schematic,
    routed_clusters: list[
        tuple[
            str,
            list[tuple[float, float]],
            list[tuple[tuple[float, float], tuple[float, float]]],
        ]
    ],
    hierarchical_nets: dict[str, str] | None = None,
) -> None:
    hierarchical_nets = hierarchical_nets or {}
    pin_positions: list[tuple[float, float]] = []
    point_to_pin: dict[tuple[float, float], tuple[str, str]] = {}
    for component in schematic.components:
        if component.reference.startswith(("#PWR", "#FLG")):
            continue
        for pin in component.pins:
            position = component_pin_position(
                schematic,
                component.reference,
                pin.number,
            )
            pin_positions.append(position)
            point_to_pin.setdefault(position, (component.reference, pin.number))

    used_label_positions: list[tuple[float, float]] = []

    for net_name, cluster_points, segments in routed_clusters:
        if segments:
            segments = sorted(
                segments,
                key=lambda segment: (
                    0 if segment[0][1] == segment[1][1] else 1,
                    -(
                        abs(segment[1][0] - segment[0][0])
                        + abs(segment[1][1] - segment[0][1])
                    ),
                ),
            )

            candidates: list[
                tuple[
                    tuple[int, float, float],
                    tuple[float, float],
                    float,
                ]
            ] = []
            for start, end in segments:
                points = _segment_grid_points(start, end)
                rotation = _label_rotation(start, end)
                for point in points[1:-1] or points:
                    pin_clearance = min(
                        abs(point[0] - pin_x) + abs(point[1] - pin_y)
                        for pin_x, pin_y in pin_positions
                    )
                    midpoint_distance = abs(
                        (point[0] - start[0]) + (point[1] - start[1])
                        - (
                            (end[0] - start[0]) + (end[1] - start[1])
                        )
                        / 2
                    )
                    score = (
                        _label_collision_count(
                            point,
                            rotation,
                            used_label_positions,
                        ),
                        -min(pin_clearance, 12.7),
                        midpoint_distance,
                    )
                    candidates.append((score, point, rotation))

            if not candidates:
                continue

            _, label_position, label_rotation = min(
                candidates,
                key=lambda item: item[0],
            )
        else:
            pin = next(
                (
                    point_to_pin[point]
                    for point in cluster_points
                    if point in point_to_pin
                ),
                None,
            )
            if pin is None:
                continue
            pin_position = component_pin_position(
                schematic,
                pin[0],
                pin[1],
            )
            endpoint, label_rotation = pin_stub(
                schematic,
                pin[0],
                pin[1],
                length_mm=LABEL_STUB_LENGTH_MM,
            )
            label_position = snap_point(
                pin_position[0]
                + (endpoint[0] - pin_position[0])
                * SINGLETON_LABEL_OFFSET_MM
                / LABEL_STUB_LENGTH_MM,
                pin_position[1]
                + (endpoint[1] - pin_position[1])
                * SINGLETON_LABEL_OFFSET_MM
                / LABEL_STUB_LENGTH_MM,
                grid_mm=GRID_MM,
            )

        if net_name in hierarchical_nets:
            schematic.add_hierarchical_label(
                net_name,
                position=label_position,
                shape=hierarchical_nets[net_name],
                rotation=label_rotation,
            )
        else:
            schematic.add_label(
                net_name,
                position=label_position,
                rotation=label_rotation,
            )
        used_label_positions.append(label_position)


def _separate_close_label_anchors(schematic) -> None:
    labels = list(schematic.labels) + list(schematic.hierarchical_labels)
    wire_segments = [
        (
            (wire.points[0].x, wire.points[0].y),
            (wire.points[-1].x, wire.points[-1].y),
        )
        for wire in schematic.wires
        if len(wire.points) >= 2
    ]
    directions = ((0.0, -1.0), (0.0, 1.0), (-1.0, 0.0), (1.0, 0.0))
    stub_lengths = (5.08, 7.62, 10.16)
    placed_positions: list[tuple[float, float]] = []

    for label in labels:
        base = (label.position.x, label.position.y)
        if not any(
            _point_on_wire(base, start, end) for start, end in wire_segments
        ):
            placed_positions.append(base)
            continue

        def collision_count(point: tuple[float, float]) -> int:
            return sum(
                1
                for existing in placed_positions
                if abs(point[0] - existing[0]) + abs(point[1] - existing[1]) < 5.08
            )

        candidates: list[
            tuple[tuple[int, int, float, tuple[float, float]], tuple[float, float]]
        ] = [((collision_count(base), 0, 0.0, base), base)]
        for length in stub_lengths:
            for direction_x, direction_y in directions:
                endpoint = snap_point(
                    base[0] + direction_x * length,
                    base[1] + direction_y * length,
                    grid_mm=GRID_MM,
                )
                if not (20.0 <= endpoint[0] <= 287.0 and 10.0 <= endpoint[1] <= 200.0):
                    continue
                crossing_count = sum(
                    1
                    for start, end in wire_segments
                    if start != base
                    and end != base
                    and segments_intersect(base, endpoint, start, end)
                )
                candidates.append(
                    (
                        (
                            collision_count(endpoint),
                            crossing_count,
                            abs(endpoint[0] - base[0]) + abs(endpoint[1] - base[1]),
                            endpoint,
                        ),
                        endpoint,
                    )
                )

        _, selected = min(candidates, key=lambda item: item[0])
        if selected != base:
            schematic.wires.add(start=base, end=selected)
            if schematic.junctions.get_at_position(base) is None:
                schematic.junctions.add(base)
            label.position = selected
        placed_positions.append(selected)


def add_power_pin(
    schematic,
    allocator: ReferenceAllocator,
    net_name: str,
    reference: str,
    pin_number: str,
    flagged_nets: set[str],
    allow_flags: bool,
) -> None:
    if f"{reference}.{pin_number}" in DIRECT_POWER_PINS:
        return

    endpoint, _ = pin_stub(schematic, reference, pin_number)
    power_ref = allocator.next_power()
    power_symbol = POWER_SYMBOLS[net_name]
    power_component = schematic.components.add(
        lib_id=power_symbol,
        reference=power_ref,
        value=net_name,
        position=endpoint,
    )
    power_component.value = net_name

    if allow_flags and net_name in POWER_FLAG_NETS and net_name not in flagged_nets:
        if net_name == "PWR_VOUT_ISO":
            flag_position = snap_point(
                endpoint[0] - 5.08,
                endpoint[1],
                grid_mm=GRID_MM,
            )
        else:
            offset = 5.08 if net_name.startswith("GND") else -5.08
            flag_position = snap_point(
                endpoint[0],
                endpoint[1] + offset,
                grid_mm=GRID_MM,
            )
        schematic.wires.add(start=endpoint, end=flag_position)
        flag_ref = allocator.next_flag()
        schematic.components.add(
            lib_id="power:PWR_FLAG",
            reference=flag_ref,
            value="PWR_FLAG",
            position=flag_position,
            rotation=180 if net_name.startswith("GND") else 0,
        )
        flagged_nets.add(net_name)


def add_components(schematic, design: dict, references: set[str]) -> None:
    for reference in sorted(references):
        component = design["components"][reference]
        schematic.components.add(
            lib_id=component["symbol"],
            reference=reference,
            value=str(component["value"]),
            position=snap_point(*POSITIONS[reference], grid_mm=GRID_MM),
            rotation=ROTATIONS.get(reference, 0),
            footprint=component["footprint"],
        )


def add_module_box(
    schematic,
    title: str,
    detail: str,
    start: tuple[float, float],
    end: tuple[float, float],
) -> None:
    start = snap_point(*start, grid_mm=GRID_MM)
    end = snap_point(*end, grid_mm=GRID_MM)
    text = title if not detail else f"{title}\n{detail}"
    schematic.add_text_box(
        text=text,
        position=start,
        size=(end[0] - start[0], end[1] - start[1]),
        font_size=1.0,
        stroke_width=0.15,
        fill_type="none",
        justify_horizontal="left",
        justify_vertical="top",
    )


def add_annotation(
    schematic,
    text: str,
    position: tuple[float, float],
) -> None:
    schematic.add_text(
        text=text,
        position=snap_point(*position, grid_mm=GRID_MM),
        size=1.0,
    )


def add_no_connects(
    schematic,
    design: dict,
    references: set[str],
) -> None:
    for connection in design.get("no_connect", []):
        reference, pin = connection.split(".", 1)
        if reference not in references:
            continue
        position = schematic.get_component_pin_position(reference, pin)
        if position is None:
            raise ValueError(f"Cannot find no-connect pin {connection}")
        schematic.no_connects.add(position)


def build_power_sheet(design: dict, allocator: ReferenceAllocator) -> None:
    schematic = create_schematic("Power")
    flagged_nets: set[str] = set()

    add_components(schematic, design, POWER_COMPONENTS)

    for net_name, net in design["nets"].items():
        for connection in net["connections"]:
            reference, pin = connection.split(".", 1)
            if reference not in POWER_COMPONENTS:
                continue
            if net_name not in POWER_NETS:
                raise ValueError(f"Unexpected non-power net {net_name} in Power sheet")
            add_power_pin(
                schematic,
                allocator,
                net_name,
                reference,
                pin,
                flagged_nets,
                allow_flags=False,
            )

    schematic.wires.add(
        start=component_pin_position(schematic, "U4", "5"),
        end=component_pin_position(schematic, "C9", "1"),
    )
    schematic.wires.add(
        start=component_pin_position(schematic, "C7", "1"),
        end=component_pin_position(schematic, "PS1", "2"),
    )
    schematic.wires.add(
        start=component_pin_position(schematic, "C8", "1"),
        end=component_pin_position(schematic, "PS1", "4"),
    )
    schematic.wires.add(
        start=component_pin_position(schematic, "U4", "5"),
        end=(243.84, 27.94),
    )
    schematic.wires.add(
        start=(243.84, 27.94),
        end=component_pin_position(schematic, "C10", "1"),
    )
    add_module_box(
        schematic,
        "USB INPUT PROTECTION",
        "F1: 0.5A PTC | C1: 4.7uF bulk",
        (34.29, 20.32),
        (90.17, 50.8),
    )
    add_module_box(
        schematic,
        "ISOLATED POWER TREE",
        "PWR_5V_USB -> PS1 -> PWR_5V_ISO -> U4 -> PWR_3V3_ISO",
        (160.02, 12.7),
        (261.62, 53.34),
    )
    add_annotation(
        schematic,
        "PS1: CRE1S0505SC / 1W / 1.5kVrms / isolated",
        (169.0, 41.91),
    )
    add_annotation(
        schematic,
        "U4: AP2112K-3.3 / SOT-23-5 / 3.3V / 600mA",
        (222.25, 41.91),
    )
    add_annotation(
        schematic,
        "TP1: PWR_5V_USB 5V +/-5%",
        (69.85, 44.45),
    )
    add_annotation(
        schematic,
        "TP2: PWR_3V3_ISO 3.3V +/-5%",
        (240.03, 44.45),
    )
    add_no_connects(schematic, design, POWER_COMPONENTS)
    assert_schematic_on_grid(schematic)
    schematic.save(POWER_PATH)


def build_communicate_sheet(design: dict, allocator: ReferenceAllocator) -> None:
    schematic = create_schematic("Communicate")
    flagged_nets: set[str] = set()
    signal_nodes: dict[str, list[tuple[float, float]]] = {}

    add_components(schematic, design, COMMUNICATE_COMPONENTS)

    for net_name, net in design["nets"].items():
        for connection in net["connections"]:
            reference, pin = connection.split(".", 1)
            if reference not in COMMUNICATE_COMPONENTS:
                continue

            if net_name in POWER_NETS:
                add_power_pin(
                    schematic,
                    allocator,
                    net_name,
                    reference,
                    pin,
                    flagged_nets,
                    allow_flags=False,
                )
            elif net_name in CROSS_SHEET_SIGNALS:
                register_signal_node(
                    signal_nodes,
                    net_name,
                    component_pin_position(schematic, reference, pin),
                )
            else:
                register_signal_node(
                    signal_nodes,
                    net_name,
                    component_pin_position(schematic, reference, pin),
                )

    add_no_connects(schematic, design, COMMUNICATE_COMPONENTS)
    routed_net_segments = route_signal_nets(schematic, signal_nodes)
    add_routed_net_labels(
        schematic,
        routed_net_segments,
        CROSS_SHEET_SIGNALS,
    )
    _separate_close_label_anchors(schematic)
    add_module_box(
        schematic,
        "USB-UART BRIDGE + STATUS",
        "U1: CH343G / SOIC-16 / 6Mbps USB-UART\nC2-C6: local decoupling bank",
        (103.51, 47.63),
        (168.28, 103.51),
    )
    add_module_box(
        schematic,
        "UART ISOLATION + SERIES TERMINATION",
        "U3: ISO7721D / SOIC-8 / 1.5kVrms / 100Mbps\nR6/R7: 33 Ohm",
        (168.28, 68.58),
        (258.45, 104.14),
    )
    add_module_box(
        schematic,
        "POWER STATUS LED",
        "PWR_3V3_USB -> D2 -> R5 -> GND",
        (91.44, 106.68),
        (142.24, 127.0),
    )
    add_annotation(
        schematic,
        "U1: CH343G / SOIC-16 / regulated 3.3V I/O",
        (105.41, 99.06),
    )
    add_annotation(
        schematic,
        "U3: ISO7721D / SOIC-8 / 1.5kVrms / 100Mbps",
        (204.47, 94.62),
    )
    assert_schematic_on_grid(schematic)
    schematic.save(COMMUNICATE_PATH)


def add_sheet_pin_label(
    schematic,
    pin_position: tuple[float, float],
    edge: str,
    net_name: str,
) -> None:
    if edge == "left":
        endpoint = (pin_position[0] - LABEL_STUB_LENGTH_MM, pin_position[1])
        rotation = 180.0
    elif edge == "right":
        endpoint = (pin_position[0] + LABEL_STUB_LENGTH_MM, pin_position[1])
        rotation = 0.0
    elif edge == "top":
        endpoint = (pin_position[0], pin_position[1] - LABEL_STUB_LENGTH_MM)
        rotation = 90.0
    elif edge == "bottom":
        endpoint = (pin_position[0], pin_position[1] + LABEL_STUB_LENGTH_MM)
        rotation = 270.0
    else:
        raise ValueError(f"Unsupported sheet pin edge: {edge}")

    endpoint = snap_point(*endpoint, grid_mm=GRID_MM)
    schematic.wires.add(start=pin_position, end=endpoint)
    schematic.add_label(net_name, position=endpoint, rotation=rotation)


def build_top_sheet(design: dict, allocator: ReferenceAllocator) -> tuple[str, str]:
    schematic = create_schematic(PROJECT_NAME)
    flagged_nets: set[str] = set()
    signal_nodes: dict[str, list[tuple[float, float]]] = {}

    add_components(schematic, design, TOP_COMPONENTS)

    communicate_sheet = schematic.add_sheet(
        name="Communicate",
        filename="Communicate.kicad_sch",
        position=(124.46, 45.72),
        size=(76.2, 55.88),
        project_name=PROJECT_NAME,
        page_number="3",
    )
    power_sheet = schematic.add_sheet(
        name="Power",
        filename="Power.kicad_sch",
        position=(124.46, 119.38),
        size=(76.2, 45.72),
        project_name=PROJECT_NAME,
        page_number="2",
    )

    sheet_pins = {
        "USB_DP": ("bidirectional", "left", 35.56),
        "USB_DM": ("bidirectional", "left", 25.4),
        "UART_TX_ISO_OUT": ("output", "right", 20.32),
        "UART_RX_ISO_IN": ("input", "right", 30.48),
    }

    for net_name, (pin_type, edge, along_edge) in sheet_pins.items():
        schematic.add_sheet_pin(
            communicate_sheet,
            net_name,
            pin_type,
            edge,
            along_edge,
        )

        sheet_x, sheet_y = 124.46, 45.72
        sheet_width, sheet_height = 76.2, 55.88
        if edge == "left":
            pin_position = (sheet_x, sheet_y + sheet_height - along_edge)
        else:
            pin_position = (sheet_x + sheet_width, sheet_y + along_edge)
        add_sheet_pin_label(schematic, pin_position, edge, net_name)
        endpoint = schematic.labels[-1].position
        register_signal_node(
            signal_nodes,
            net_name,
            (endpoint.x, endpoint.y),
        )

    for net_name, net in design["nets"].items():
        for connection in net["connections"]:
            reference, pin = connection.split(".", 1)
            if reference not in TOP_COMPONENTS:
                continue

            if net_name in POWER_NETS:
                add_power_pin(
                    schematic,
                    allocator,
                    net_name,
                    reference,
                    pin,
                    flagged_nets,
                    allow_flags=True,
                )
            elif net_name in CROSS_SHEET_SIGNALS:
                register_signal_node(
                    signal_nodes,
                    net_name,
                    component_pin_position(schematic, reference, pin),
                )
            else:
                register_signal_node(
                    signal_nodes,
                    net_name,
                    component_pin_position(schematic, reference, pin),
                )

    add_no_connects(schematic, design, TOP_COMPONENTS)
    routed_net_segments = route_signal_nets(schematic, signal_nodes)
    add_routed_net_labels(
        schematic,
        routed_net_segments,
    )
    _separate_close_label_anchors(schematic)
    add_module_box(
        schematic,
        "USB-C INPUT + ESD + CC",
        "J1: USB-C 2.0 16P | U2: USBLC6-2SC6 | R1/R2: 5.1k",
        (34.29, 105.41),
        (110.49, 149.86),
    )
    add_module_box(
        schematic,
        "ISOLATED UART OUTPUT",
        "J2: 1x4 2.54mm\nJP1: 1-2=PWR_3V3_ISO default, 2-3=PWR_5V_ISO",
        (228.6, 46.99),
        (283.21, 104.14),
    )
    add_module_box(
        schematic,
        "POWER FLOW",
        "PWR_5V_RAW -> [F1/ESD] -> PWR_5V_USB -> [PS1] -> PWR_5V_ISO -> [U4] -> PWR_3V3_ISO",
        (96.52, 10.16),
        (210.82, 25.4),
    )
    add_annotation(
        schematic,
        "U2: USBLC6-2SC6 / SOT-23-6 / USB ESD",
        (78.74, 139.7),
    )
    add_annotation(
        schematic,
        "J1: USB-C 2.0 16P / 5V sink",
        (36.83, 145.42),
    )
    add_annotation(
        schematic,
        "TP3: UART_TX_ISO_OUT / 3.3V / <=5Mbps",
        (233.68, 69.85),
    )
    add_annotation(
        schematic,
        "TP4: UART_RX_ISO_IN / 3.3V / <=5Mbps",
        (233.68, 99.06),
    )
    assert_schematic_on_grid(schematic)
    schematic.save(TOP_PATH)
    return communicate_sheet, power_sheet


def update_project_file(root_uuid: str, power_uuid: str, communicate_uuid: str) -> None:
    project_data = json.loads(PROJECT_PATH.read_text(encoding="utf-8"))
    project_data.setdefault("meta", {})
    project_data["meta"]["filename"] = PROJECT_PATH.name
    project_data.setdefault("schematic", {})[
        "page_layout_descr_file"
    ] = DRAWING_SHEET_NAME
    project_data["sheets"] = [
        [root_uuid, PROJECT_NAME],
        [power_uuid, "Power"],
        [communicate_uuid, "Communicate"],
    ]
    PROJECT_PATH.write_text(
        json.dumps(project_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def upgrade_schematics_to_current_format() -> None:
    if not KICAD_CLI.exists():
        raise FileNotFoundError(f"KiCad CLI not found: {KICAD_CLI}")

    for schematic_path in (POWER_PATH, COMMUNICATE_PATH, TOP_PATH):
        subprocess.run(
            [
                str(KICAD_CLI),
                "sch",
                "upgrade",
                "--force",
                str(schematic_path),
            ],
            check=True,
        )


def force_visible_pin_numbers() -> None:
    pattern = re.compile(r"\(pin_numbers\s*\(hide yes\)\s*\)")
    for schematic_path in (POWER_PATH, COMMUNICATE_PATH, TOP_PATH):
        content = schematic_path.read_text(encoding="utf-8")
        updated = pattern.sub("(pin_numbers)", content)
        if updated != content:
            schematic_path.write_text(updated, encoding="utf-8")


def main() -> None:
    HARDWARE_DIR.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / ".pyhome").mkdir(parents=True, exist_ok=True)

    design = load_design()
    allocator = ReferenceAllocator()
    build_power_sheet(design, allocator)
    build_communicate_sheet(design, allocator)
    communicate_sheet, power_sheet = build_top_sheet(design, allocator)

    root = ksa.load_schematic(TOP_PATH)
    update_project_file(root.uuid, power_sheet, communicate_sheet)
    upgrade_schematics_to_current_format()
    force_visible_pin_numbers()

    print(f"Generated hierarchy: {TOP_PATH.name}, {POWER_PATH.name}, {COMMUNICATE_PATH.name}")
    print("Upgraded all schematics to the installed KiCad 10.0 format")
    print(f"Root UUID: {root.uuid}")
    print(f"Power sheet UUID: {power_sheet}")
    print(f"Communicate sheet UUID: {communicate_sheet}")


if __name__ == "__main__":
    main()
