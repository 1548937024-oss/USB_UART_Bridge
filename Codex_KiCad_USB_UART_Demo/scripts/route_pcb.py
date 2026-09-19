from pathlib import Path
import heapq
import math
import os
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools" / "python"))

import numpy as np
import pcbnew
import yaml


HARDWARE_DIR = PROJECT_ROOT / "hardware" / "USB_UART_Bridge"
BOARD_PATH = HARDWARE_DIR / "USB_UART_Bridge.kicad_pcb"
ROUTING_DIR = PROJECT_ROOT / "generated" / "routing"
DSN_PATH = ROUTING_DIR / "USB_UART_Bridge.dsn"
SES_PATH = ROUTING_DIR / "USB_UART_Bridge.ses"
FROZEN_SES_PATH = ROUTING_DIR / "USB_UART_Bridge_frozen.ses"
FREEROUTING_EXE = (
    PROJECT_ROOT
    / ".tools"
    / "freerouting-2.4.1"
    / "freerouting"
    / "freerouting.exe"
)
DESIGN_RULES_PATH = PROJECT_ROOT / "pcb_design_rules.yaml"

GRID_MM = 0.25
MIN_TRACK_WIDTH_MM = 0.20
GROUND_TRACK_WIDTH_MM = 0.50
POWER_TRACK_WIDTH_MM = 0.22
POWER_VIA_DIAMETER_MM = 0.60
POWER_VIA_DRILL_MM = 0.30
PAD_ESCAPE_EXTRA_MM = 0.35
CLEARANCE_MM = 0.20
EDGE_MARGIN_MM = 0.20
USB_SIDE_MAX_X_MM = 148.45
GROUND_NET_NAMES = {"GND", "ISO_GND"}


def mm(value: float) -> int:
    return pcbnew.FromMM(float(value))


def load_rules() -> dict:
    with DESIGN_RULES_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def export_dsn(board) -> None:
    ROUTING_DIR.mkdir(parents=True, exist_ok=True)
    if not pcbnew.ExportSpecctraDSN(board, str(DSN_PATH)):
        raise RuntimeError(f"Failed to export Specctra DSN: {DSN_PATH}")


def run_freerouting() -> None:
    if FROZEN_SES_PATH.exists():
        shutil.copyfile(FROZEN_SES_PATH, SES_PATH)
        return
    if not FREEROUTING_EXE.exists():
        raise FileNotFoundError(
            "FreeRouting is missing. Expected: "
            f"{FREEROUTING_EXE}. See README for the project-local setup."
        )

    freerouting_home = PROJECT_ROOT / ".tools" / "freerouting-home"
    freerouting_home.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["JAVA_TOOL_OPTIONS"] = (
        f"-Duser.home={freerouting_home} "
        f"-Djava.io.tmpdir={freerouting_home}"
    )
    command = [
        str(FREEROUTING_EXE),
        "-de",
        str(DSN_PATH),
        "-do",
        str(SES_PATH),
        "-mp",
        "50",
        "-mt",
        "1",
        "-us",
        "global",
    ]
    log_path = ROUTING_DIR / "freerouting.log"
    with log_path.open("w", encoding="utf-8", errors="replace") as log_handle:
        subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
        )


def import_ses(board) -> None:
    if not SES_PATH.exists():
        raise FileNotFoundError(f"FreeRouting did not create: {SES_PATH}")
    if not pcbnew.ImportSpecctraSES(board, str(SES_PATH)):
        raise RuntimeError(f"Failed to import Specctra SES: {SES_PATH}")


def is_power_net(net_name: str) -> bool:
    return net_name in GROUND_NET_NAMES or net_name.startswith("PWR_")


def track_width_for_net(net_name: str) -> float:
    if net_name in GROUND_NET_NAMES:
        return GROUND_TRACK_WIDTH_MM
    if net_name.startswith("PWR_"):
        return POWER_TRACK_WIDTH_MM
    return MIN_TRACK_WIDTH_MM


def pad_long_axis(pad, outward: tuple[float, float]) -> tuple[tuple[float, float], float]:
    size = pad.GetSize()
    size_x = pcbnew.ToMM(size.x)
    size_y = pcbnew.ToMM(size.y)
    angle = math.radians(pad.GetOrientationDegrees())
    if size_x >= size_y:
        axis = (math.cos(angle), math.sin(angle))
        half_length = size_x / 2.0
    else:
        axis = (-math.sin(angle), math.cos(angle))
        half_length = size_y / 2.0

    if axis[0] * outward[0] + axis[1] * outward[1] < 0:
        axis = (-axis[0], -axis[1])
    return axis, half_length


def pad_contains_point(pad, point: tuple[float, float], margin_mm: float = 0.01) -> bool:
    center = pad.GetPosition()
    center_x = pcbnew.ToMM(center.x)
    center_y = pcbnew.ToMM(center.y)
    size = pad.GetSize()
    size_x = pcbnew.ToMM(size.x)
    size_y = pcbnew.ToMM(size.y)
    angle = math.radians(pad.GetOrientationDegrees())
    dx = point[0] - center_x
    dy = point[1] - center_y
    local_x = dx * math.cos(angle) + dy * math.sin(angle)
    local_y = -dx * math.sin(angle) + dy * math.cos(angle)
    return (
        abs(local_x) <= size_x / 2.0 + margin_mm
        and abs(local_y) <= size_y / 2.0 + margin_mm
    )


def snap_smd_pad_connections_to_center(board) -> int:
    """Move track endpoints inside connected SMD pads back to the pad center."""
    changed = 0
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue

            net = pad.GetNet()
            if net is None:
                continue
            net_name = net.GetNetname()
            if (
                not net_name
                or net_name.startswith("unconnected-")
                or net_name in GROUND_NET_NAMES
            ):
                continue

            center = pad.GetPosition()
            center_mm = pcbnew.ToMM(center.x), pcbnew.ToMM(center.y)
            for item in board.GetTracks():
                if isinstance(item, pcbnew.PCB_VIA):
                    continue
                if item.GetNetCode() != net.GetNetCode():
                    continue
                start = item.GetStart()
                end = item.GetEnd()
                start_mm = pcbnew.ToMM(start.x), pcbnew.ToMM(start.y)
                end_mm = pcbnew.ToMM(end.x), pcbnew.ToMM(end.y)
                if pad_contains_point(pad, start_mm):
                    if (
                        abs(start_mm[0] - center_mm[0]) > 0.01
                        or abs(start_mm[1] - center_mm[1]) > 0.01
                    ):
                        item.SetStart(pcbnew.VECTOR2I_MM(*center_mm))
                        changed += 1
                elif pad_contains_point(pad, end_mm):
                    if (
                        abs(end_mm[0] - center_mm[0]) > 0.01
                        or abs(end_mm[1] - center_mm[1]) > 0.01
                    ):
                        item.SetEnd(pcbnew.VECTOR2I_MM(*center_mm))
                        changed += 1
    return changed


def normalize_track_widths(board) -> int:
    changed = 0
    for item in board.GetTracks():
        if isinstance(item, pcbnew.PCB_VIA):
            continue
        if item.GetWidth() < mm(MIN_TRACK_WIDTH_MM):
            item.SetWidth(mm(MIN_TRACK_WIDTH_MM))
            changed += 1
    return changed


def enforce_power_track_widths(board) -> int:
    changed = 0
    for item in board.GetTracks():
        if isinstance(item, pcbnew.PCB_VIA):
            continue
        target_width = track_width_for_net(item.GetNetname())
        if item.GetWidth() < mm(target_width):
            item.SetWidth(mm(target_width))
            changed += 1
    return changed


def fix_usb_cc2_escape(board) -> None:
    for item in board.GetTracks():
        if item.GetNetname() != "/USB_CC2":
            continue
        if isinstance(item, pcbnew.PCB_VIA):
            position = item.GetPosition()
            x = pcbnew.ToMM(position.x)
            y = pcbnew.ToMM(position.y)
            if abs(x - 127.491) < 0.01 and abs(y - 106.683) < 0.01:
                item.SetPosition(pcbnew.VECTOR2I_MM(127.491, 106.750))
            continue

        start = item.GetStart()
        end = item.GetEnd()
        start_xy = (pcbnew.ToMM(start.x), pcbnew.ToMM(start.y))
        end_xy = (pcbnew.ToMM(end.x), pcbnew.ToMM(end.y))
        for xy, setter in ((start_xy, item.SetStart), (end_xy, item.SetEnd)):
            if (
                abs(xy[1] - 106.683) < 0.01
                and (
                    abs(xy[0] - 127.491) < 0.01
                    or abs(xy[0] - 128.603) < 0.01
                )
            ):
                setter(pcbnew.VECTOR2I_MM(xy[0], 106.750))


def point_segment_distance(
    xs: np.ndarray,
    ys: np.ndarray,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> np.ndarray:
    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-12:
        return np.hypot(xs - x1, ys - y1)
    t = ((xs - x1) * dx + (ys - y1) * dy) / length_sq
    t = np.clip(t, 0.0, 1.0)
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    return np.hypot(xs - closest_x, ys - closest_y)


def build_grid(board, netcode: int, route_width_mm: float, usb_side_only: bool):
    bounds = board.GetBoardEdgesBoundingBox()
    min_x = pcbnew.ToMM(bounds.GetX())
    min_y = pcbnew.ToMM(bounds.GetY())
    max_x = pcbnew.ToMM(bounds.GetX() + bounds.GetWidth())
    max_y = pcbnew.ToMM(bounds.GetY() + bounds.GetHeight())

    x_values = np.arange(
        min_x + EDGE_MARGIN_MM,
        max_x - EDGE_MARGIN_MM + GRID_MM / 2.0,
        GRID_MM,
    )
    y_values = np.arange(
        min_y + EDGE_MARGIN_MM,
        max_y - EDGE_MARGIN_MM + GRID_MM / 2.0,
        GRID_MM,
    )
    xs, ys = np.meshgrid(x_values, y_values)
    blocked = np.zeros(xs.shape, dtype=bool)

    if usb_side_only:
        blocked |= xs > USB_SIDE_MAX_X_MM

    route_half_width = route_width_mm / 2.0

    for item in board.GetTracks():
        if item.GetNetCode() == netcode:
            continue
        if isinstance(item, pcbnew.PCB_VIA):
            center = item.GetPosition()
            radius = (
                pcbnew.ToMM(item.GetWidth(pcbnew.F_Cu)) / 2.0
                + CLEARANCE_MM
                + route_half_width
            )
            blocked |= np.hypot(
                xs - pcbnew.ToMM(center.x),
                ys - pcbnew.ToMM(center.y),
            ) < radius
            continue

        if item.GetLayer() != pcbnew.B_Cu:
            continue
        start = item.GetStart()
        end = item.GetEnd()
        radius = (
            pcbnew.ToMM(item.GetWidth()) / 2.0
            + CLEARANCE_MM
            + route_half_width
        )
        distance = point_segment_distance(
            xs,
            ys,
            pcbnew.ToMM(start.x),
            pcbnew.ToMM(start.y),
            pcbnew.ToMM(end.x),
            pcbnew.ToMM(end.y),
        )
        blocked |= distance < radius

    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetNetCode() == netcode:
                continue
            if not pad.IsOnLayer(pcbnew.B_Cu):
                continue
            center = pad.GetPosition()
            size = pad.GetSize()
            radius = (
                max(pcbnew.ToMM(size.x), pcbnew.ToMM(size.y)) / 2.0
                + CLEARANCE_MM
                + route_half_width
            )
            blocked |= np.hypot(
                xs - pcbnew.ToMM(center.x),
                ys - pcbnew.ToMM(center.y),
            ) < radius

    return x_values, y_values, blocked


def nearest_free_index(
    x_values: np.ndarray,
    y_values: np.ndarray,
    blocked: np.ndarray,
    x_mm: float,
    y_mm: float,
) -> tuple[int, int]:
    ix = int(np.argmin(np.abs(x_values - x_mm)))
    iy = int(np.argmin(np.abs(y_values - y_mm)))
    if not blocked[iy, ix]:
        return ix, iy

    rows, cols = blocked.shape
    for radius in range(1, 17):
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if abs(dx) != radius and abs(dy) != radius:
                    continue
                nx = ix + dx
                ny = iy + dy
                if 0 <= nx < cols and 0 <= ny < rows and not blocked[ny, nx]:
                    return nx, ny
    raise RuntimeError(f"No free routing cell near ({x_mm:.3f}, {y_mm:.3f})")


def find_grid_path(
    x_values: np.ndarray,
    y_values: np.ndarray,
    blocked: np.ndarray,
    start_mm: tuple[float, float],
    end_mm: tuple[float, float],
) -> list[tuple[float, float]]:
    start_x, start_y = nearest_free_index(
        x_values,
        y_values,
        blocked,
        *start_mm,
    )
    end_x, end_y = nearest_free_index(
        x_values,
        y_values,
        blocked,
        *end_mm,
    )
    rows, cols = blocked.shape
    start = (start_x, start_y)
    end = (end_x, end_y)

    open_queue = [(0.0, start)]
    costs = {start: 0.0}
    previous = {}

    while open_queue:
        _, current = heapq.heappop(open_queue)
        if current == end:
            break

        cx, cy = current
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx = cx + dx
            ny = cy + dy
            if not (0 <= nx < cols and 0 <= ny < rows):
                continue
            if blocked[ny, nx]:
                continue
            new_cost = costs[current] + 1.0
            neighbor = (nx, ny)
            if new_cost >= costs.get(neighbor, float("inf")):
                continue
            costs[neighbor] = new_cost
            previous[neighbor] = current
            heuristic = abs(nx - end[0]) + abs(ny - end[1])
            heapq.heappush(
                open_queue,
                (new_cost + heuristic, neighbor),
            )

    if end not in previous and end != start:
        raise RuntimeError(
            f"No two-layer route found from {start_mm} to {end_mm}"
        )

    grid_path = [end]
    while grid_path[-1] != start:
        grid_path.append(previous[grid_path[-1]])
    grid_path.reverse()

    points = [
        (float(x_values[ix]), float(y_values[iy]))
        for ix, iy in grid_path
    ]
    simplified = [points[0]]
    for point in points[1:]:
        if len(simplified) < 2:
            simplified.append(point)
            continue
        x0, y0 = simplified[-2]
        x1, y1 = simplified[-1]
        x2, y2 = point
        if (x0 == x1 == x2) or (y0 == y1 == y2):
            simplified[-1] = point
        else:
            simplified.append(point)
    return simplified


def add_track(
    board,
    netcode: int,
    width_mm: float,
    start: tuple[float, float],
    end: tuple[float, float],
    layer=pcbnew.B_Cu,
) -> None:
    track = pcbnew.PCB_TRACK(board)
    track.SetNetCode(netcode)
    track.SetLayer(layer)
    track.SetWidth(mm(width_mm))
    track.SetStart(pcbnew.VECTOR2I_MM(*start))
    track.SetEnd(pcbnew.VECTOR2I_MM(*end))
    board.Add(track)


def add_via(board, netcode: int, position: tuple[float, float]) -> None:
    via = pcbnew.PCB_VIA(board)
    via.SetNetCode(netcode)
    via.SetPosition(pcbnew.VECTOR2I_MM(*position))
    via.SetWidth(mm(POWER_VIA_DIAMETER_MM))
    via.SetDrill(mm(POWER_VIA_DRILL_MM))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(via)


def find_or_add_via(
    board,
    netcode: int,
    position: tuple[float, float],
    tolerance_mm: float = 0.05,
):
    for item in board.GetTracks():
        if not isinstance(item, pcbnew.PCB_VIA):
            continue
        if item.GetNetCode() != netcode:
            continue
        center = item.GetPosition()
        if (
            abs(pcbnew.ToMM(center.x) - position[0]) <= tolerance_mm
            and abs(pcbnew.ToMM(center.y) - position[1]) <= tolerance_mm
        ):
            return item
    add_via(board, netcode, position)
    return None


def add_grid_route(
    board,
    netcode: int,
    start_mm: tuple[float, float],
    end_mm: tuple[float, float],
    width_mm: float,
    usb_side_only: bool,
) -> None:
    x_values, y_values, blocked = build_grid(
        board,
        netcode,
        width_mm,
        usb_side_only,
    )
    points = find_grid_path(
        x_values,
        y_values,
        blocked,
        start_mm,
        end_mm,
    )
    if points[0] != start_mm:
        add_track(board, netcode, width_mm, start_mm, points[0])
    for start, end in zip(points, points[1:]):
        add_track(board, netcode, width_mm, start, end)
    if points[-1] != end_mm:
        add_track(board, netcode, width_mm, points[-1], end_mm)


def add_copper_zone(
    board,
    netcode: int,
    bounds_mm: tuple[float, float, float, float],
    layer: int,
    pad_connection=pcbnew.ZONE_CONNECTION_THERMAL,
) -> None:
    zone = pcbnew.ZONE(board)
    zone.SetNetCode(netcode)
    zone.SetPadConnection(pad_connection)
    zone.SetLocalClearance(mm(CLEARANCE_MM))
    zone.SetMinThickness(mm(0.20))

    layer_set = pcbnew.LSET()
    layer_set.addLayer(layer)
    zone.SetLayerSet(layer_set)

    x1, y1, x2, y2 = bounds_mm
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
        outline.Append(mm(x), mm(y))
    board.Add(zone)
    zone.SetNetCode(netcode)


def add_ground_zones(board) -> None:
    bounds = board.GetBoardEdgesBoundingBox()
    left = pcbnew.ToMM(bounds.GetX()) + 1.00
    top = pcbnew.ToMM(bounds.GetY()) + 1.00
    right = pcbnew.ToMM(bounds.GetX() + bounds.GetWidth()) - 1.00
    bottom = pcbnew.ToMM(bounds.GetY() + bounds.GetHeight()) - 1.00

    gnd = board.FindNet("GND")
    iso_gnd = board.FindNet("ISO_GND")
    if gnd is None or iso_gnd is None:
        raise RuntimeError("GND or ISO_GND net not found")

    add_copper_zone(
        board,
        gnd.GetNetCode(),
        (left, top, USB_SIDE_MAX_X_MM - 0.10, bottom),
        pcbnew.B_Cu,
        pad_connection=pcbnew.ZONE_CONNECTION_FULL,
    )
    add_copper_zone(
        board,
        iso_gnd.GetNetCode(),
        (154.50, top, right, bottom),
        pcbnew.B_Cu,
        pad_connection=pcbnew.ZONE_CONNECTION_THERMAL,
    )


def add_local_power_zone(board) -> None:
    net = board.FindNet("PWR_5V_ISO")
    if net is None:
        raise RuntimeError("PWR_5V_ISO net not found")
    add_copper_zone(
        board,
        net.GetNetCode(),
        (160.75, 103.25, 166.60, 108.75),
        pcbnew.F_Cu,
        pad_connection=pcbnew.ZONE_CONNECTION_FULL,
    )


def fill_zones(board) -> None:
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())


def find_pad(board, reference: str, pin: str):
    footprint = board.FindFootprintByReference(reference)
    if footprint is None:
        raise RuntimeError(f"Footprint not found: {reference}")
    matches = [pad for pad in footprint.Pads() if pad.GetNumber() == pin]
    if not matches:
        raise RuntimeError(f"Pad not found: {reference}.{pin}")
    return matches[0]


def pad_center_mm(pad) -> tuple[float, float]:
    position = pad.GetPosition()
    return pcbnew.ToMM(position.x), pcbnew.ToMM(position.y)


def route_pwr_vout_iso(board) -> None:
    net = board.FindNet("PWR_VOUT_ISO")
    if net is None:
        raise RuntimeError("Net not found: PWR_VOUT_ISO")
    jp1_pad = find_pad(board, "JP1", "2")
    j2_pad = find_pad(board, "J2", "2")
    route_width = POWER_TRACK_WIDTH_MM
    route_x = 174.85
    points = [
        pad_center_mm(jp1_pad),
        (route_x, 99.54),
        (route_x, 108.54),
        pad_center_mm(j2_pad),
    ]
    for start, end in zip(points, points[1:]):
        add_track(board, net.GetNetCode(), route_width, start, end)


def route_pwr_3v3_usb(board) -> None:
    net = board.FindNet("PWR_3V3_USB")
    if net is None:
        raise RuntimeError("Net not found: PWR_3V3_USB")
    netcode = net.GetNetCode()
    u3_pad = find_pad(board, "U3", "1")
    u1_goal_via = (146.703, 105.095)

    find_or_add_via(board, netcode, u1_goal_via)
    add_track(
        board,
        netcode,
        POWER_TRACK_WIDTH_MM,
        pad_center_mm(u3_pad),
        u1_goal_via,
        layer=pcbnew.F_Cu,
    )


def route_c7_ground(board) -> None:
    net = board.FindNet("GND")
    if net is None:
        raise RuntimeError("Net not found: GND")
    pad = find_pad(board, "C7", "2")
    via_position = (140.500, 91.500)
    find_or_add_via(board, net.GetNetCode(), via_position)
    add_track(
        board,
        net.GetNetCode(),
        GROUND_TRACK_WIDTH_MM,
        pad_center_mm(pad),
        via_position,
        layer=pcbnew.F_Cu,
    )


def route_u4_input(board) -> None:
    net = board.FindNet("PWR_5V_ISO")
    if net is None:
        raise RuntimeError("Net not found: PWR_5V_ISO")
    c8_pad = find_pad(board, "C8", "1")
    u4_pad = find_pad(board, "U4", "1")
    c8 = pad_center_mm(c8_pad)
    u4 = pad_center_mm(u4_pad)
    corner = (u4[0], c8[1])
    add_track(
        board,
        net.GetNetCode(),
        POWER_TRACK_WIDTH_MM,
        c8,
        corner,
        layer=pcbnew.F_Cu,
    )
    add_track(
        board,
        net.GetNetCode(),
        POWER_TRACK_WIDTH_MM,
        corner,
        u4,
        layer=pcbnew.F_Cu,
    )


def route_uart_tx_iso_out(board) -> None:
    net = board.FindNet("/UART_TX_ISO_OUT")
    if net is None:
        raise RuntimeError("Net not found: /UART_TX_ISO_OUT")
    j2_tx = find_pad(board, "J2", "3")
    tp3_tx = find_pad(board, "TP3", "1")
    netcode = net.GetNetCode()
    via_position = (158.000, 105.500)
    points = [
        pad_center_mm(j2_tx),
        (172.000, 111.080),
        (172.000, 110.000),
        (158.000, 110.000),
        via_position,
    ]
    for start, end in zip(points, points[1:]):
        add_track(
            board,
            netcode,
            MIN_TRACK_WIDTH_MM,
            start,
            end,
            layer=pcbnew.B_Cu,
        )
    add_via(board, netcode, via_position)
    add_track(
        board,
        netcode,
        MIN_TRACK_WIDTH_MM,
        via_position,
        pad_center_mm(tp3_tx),
        layer=pcbnew.F_Cu,
    )


def main() -> None:
    if not FROZEN_SES_PATH.exists() and not FREEROUTING_EXE.exists():
        raise FileNotFoundError(
            "FreeRouting is missing. Install it under "
            f"{FREEROUTING_EXE.parent} before routing."
        )

    rules = load_rules()
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "generate_pcb.py")],
        cwd=PROJECT_ROOT,
        check=True,
    )
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    if board is None:
        raise FileNotFoundError(BOARD_PATH)

    export_dsn(board)
    run_freerouting()
    import_ses(board)
    pcbnew.SaveBoard(str(BOARD_PATH), board)
    board = pcbnew.LoadBoard(str(BOARD_PATH))

    fix_usb_cc2_escape(board)
    changed = normalize_track_widths(board)
    power_changed = enforce_power_track_widths(board)
    route_pwr_vout_iso(board)
    route_c7_ground(board)
    route_u4_input(board)
    add_ground_zones(board)
    add_local_power_zone(board)
    fill_zones(board)

    board.BuildConnectivity()
    pcbnew.SaveBoard(str(BOARD_PATH), board)
    print(f"Routed PCB: {BOARD_PATH}")
    print(f"Normalized {changed} undersized tracks to {MIN_TRACK_WIDTH_MM:.2f} mm")
    print(
        f"Raised {power_changed} power/ground tracks to class minimum widths "
        f"({POWER_TRACK_WIDTH_MM:.2f}/{GROUND_TRACK_WIDTH_MM:.2f} mm)"
    )
    print("Added PWR_VOUT_ISO fallback routing and copper fills")
    print(
        "Track width rules: "
        f"{rules['project_design_limits']['trace_width_mm_min']:.2f} mm minimum"
    )


if __name__ == "__main__":
    sys.exit(main())
