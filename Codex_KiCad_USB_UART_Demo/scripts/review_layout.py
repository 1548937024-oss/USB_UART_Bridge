from pathlib import Path
import math

import pcbnew


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = (
    PROJECT_ROOT / "hardware" / "USB_UART_Bridge" / "USB_UART_Bridge.kicad_pcb"
)


def mm(value: int) -> float:
    return pcbnew.ToMM(value)


def pad(board, reference: str, number: str):
    footprint = board.FindFootprintByReference(reference)
    if footprint is None:
        raise RuntimeError(f"Footprint not found: {reference}")
    for candidate in footprint.Pads():
        if candidate.GetNumber() == number:
            return candidate
    raise RuntimeError(f"Pad not found: {reference}.{number}")


def pad_xy(board, reference: str, number: str) -> tuple[float, float]:
    position = pad(board, reference, number).GetPosition()
    return mm(position.x), mm(position.y)


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def point_line_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-12:
        return distance(point, start)
    t = (
        (point[0] - start[0]) * dx + (point[1] - start[1]) * dy
    ) / length_sq
    t = max(0.0, min(1.0, t))
    closest = (start[0] + t * dx, start[1] + t * dy)
    return distance(point, closest)


def footprint_bounds(footprint) -> tuple[float, float, float, float]:
    box = footprint.GetBoundingBox(False, False)
    return (
        mm(box.GetX()),
        mm(box.GetY()),
        mm(box.GetX() + box.GetWidth()),
        mm(box.GetY() + box.GetHeight()),
    )


def rectangle_gap(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> float:
    dx = max(left[0] - right[2], right[0] - left[2], 0.0)
    dy = max(left[1] - right[3], right[1] - left[3], 0.0)
    return max(dx, dy)


def main() -> None:
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    if board is None:
        raise FileNotFoundError(BOARD_PATH)

    board_box = board.GetBoardEdgesBoundingBox()
    board_bounds = (
        mm(board_box.GetX()),
        mm(board_box.GetY()),
        mm(board_box.GetX() + board_box.GetWidth()),
        mm(board_box.GetY() + board_box.GetHeight()),
    )
    print(
        "Board bounds: "
        f"({board_bounds[0]:.2f}, {board_bounds[1]:.2f}) - "
        f"({board_bounds[2]:.2f}, {board_bounds[3]:.2f})"
    )

    print("\nPlacement:")
    bounds_by_reference = {}
    for footprint in sorted(board.GetFootprints(), key=lambda item: item.GetReference()):
        reference = footprint.GetReference()
        if not reference or reference.startswith("#"):
            continue
        x1, y1, x2, y2 = footprint_bounds(footprint)
        bounds_by_reference[reference] = (x1, y1, x2, y2)
        position = footprint.GetPosition()
        print(
            f"{reference:>4}  pos=({mm(position.x):6.2f},{mm(position.y):6.2f})  "
            f"rot={footprint.GetOrientationDegrees():5.1f}  "
            f"edge=({x1 - board_bounds[0]:5.2f},"
            f"{y1 - board_bounds[1]:5.2f},"
            f"{board_bounds[2] - x2:5.2f},"
            f"{board_bounds[3] - y2:5.2f})"
        )

    print("\nTight footprint clearances (<0.5 mm):")
    references = sorted(bounds_by_reference)
    for index, reference in enumerate(references):
        for other in references[index + 1 :]:
            gap = rectangle_gap(
                bounds_by_reference[reference],
                bounds_by_reference[other],
            )
            if gap < 0.5:
                print(f"{reference:<4} <-> {other:<4} {gap:5.2f} mm")

    print("\nDecoupling distances:")
    distances = [
        ("C2.1 -> U1.4 V3", "C2", "1", "U1", "4"),
        ("C3.1 -> U1.4 V3", "C3", "1", "U1", "4"),
        ("C4.1 -> U1.15 VIO", "C4", "1", "U1", "15"),
        ("C5.1 -> U1.15 VIO", "C5", "1", "U1", "15"),
        ("C6.1 -> U1.15 VIO", "C6", "1", "U1", "15"),
        ("C7.1 -> PS1.2 +VIN", "C7", "1", "PS1", "2"),
        ("C8.1 -> PS1.4 +VOUT", "C8", "1", "PS1", "4"),
        ("C8.1 -> U4.1 VIN", "C8", "1", "U4", "1"),
        ("C9.1 -> U4.5 VOUT", "C9", "1", "U4", "5"),
        ("C10.1 -> U4.5 VOUT", "C10", "1", "U4", "5"),
        ("C11.1 -> U3.8 VCC2", "C11", "1", "U3", "8"),
        ("C12.1 -> U3.8 VCC2", "C12", "1", "U3", "8"),
    ]
    for label, ref_a, pin_a, ref_b, pin_b in distances:
        value = distance(
            pad_xy(board, ref_a, pin_a),
            pad_xy(board, ref_b, pin_b),
        )
        print(f"{label:<24} {value:5.2f} mm")

    print("\nLED loop distances:")
    led_measurements = [
        ("U1.8 -> R4.2", "U1", "8", "R4", "2"),
        ("R4.1 -> D1.1", "R4", "1", "D1", "1"),
        ("D1.2 -> C6.1 PWR_3V3", "D1", "2", "C6", "1"),
        ("D2.2 -> C2.1 PWR_3V3", "D2", "2", "C2", "1"),
        ("D2.1 -> R5.1", "D2", "1", "R5", "1"),
        ("R5.2 -> C2.2 GND", "R5", "2", "C2", "2"),
    ]
    for label, ref_a, pin_a, ref_b, pin_b in led_measurements:
        value = distance(
            pad_xy(board, ref_a, pin_a),
            pad_xy(board, ref_b, pin_b),
        )
        print(f"{label:<28} {value:5.2f} mm")

    print("\n5 Mbps UART chain distances:")
    uart_measurements = [
        ("U1.2 -> R6.1", "U1", "2", "R6", "1"),
        ("R6.2 -> U3.3", "R6", "2", "U3", "3"),
        ("U3.7 -> R7.1", "U3", "7", "R7", "1"),
        ("R7.2 -> J2.4", "R7", "2", "J2", "4"),
    ]
    for label, ref_a, pin_a, ref_b, pin_b in uart_measurements:
        value = distance(
            pad_xy(board, ref_a, pin_a),
            pad_xy(board, ref_b, pin_b),
        )
        print(f"{label:<20} {value:5.2f} mm")

    print("\nUART test point alignment:")
    tx_line = (pad_xy(board, "U3", "6"), pad_xy(board, "J2", "3"))
    rx_line = (pad_xy(board, "U3", "7"), pad_xy(board, "J2", "4"))
    print(
        "TP3 -> TX line          "
        f"{point_line_distance(pad_xy(board, 'TP3', '1'), *tx_line):5.2f} mm"
    )
    print(
        "TP4 -> RX line          "
        f"{point_line_distance(pad_xy(board, 'TP4', '1'), *rx_line):5.2f} mm"
    )


if __name__ == "__main__":
    main()
