#!/usr/bin/env python3
"""Build the rigid-flex board outline on Edge.Cuts.

The board is a union of two circular rigid islands and one straight flex
bridge.  The bridge length is the clear distance between the two circles;
the total center-to-center distance is therefore:

    diameter + flex_length = 2 * radius + flex_length

Coordinates are millimetres in the PCB page coordinate system.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import pcbnew

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOARD = PROJECT_ROOT / "LA150C_RDIVER_V1.00.kicad_pcb"


def mm_point(x_mm: float, y_mm: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm))


def remove_existing_edge_cuts(board: pcbnew.BOARD) -> int:
    removed = 0
    for item in list(board.GetDrawings()):
        if item.GetLayer() == pcbnew.Edge_Cuts:
            board.Remove(item)
            removed += 1
    return removed


def add_segment(
    board: pcbnew.BOARD,
    start: tuple[float, float],
    end: tuple[float, float],
    width_mm: float,
) -> None:
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
    shape.SetLayer(pcbnew.Edge_Cuts)
    shape.SetWidth(pcbnew.FromMM(width_mm))
    shape.SetStart(mm_point(*start))
    shape.SetEnd(mm_point(*end))
    shape.SetFilled(False)
    board.Add(shape)


def add_arc(
    board: pcbnew.BOARD,
    start: tuple[float, float],
    mid: tuple[float, float],
    end: tuple[float, float],
    width_mm: float,
) -> None:
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(pcbnew.SHAPE_T_ARC)
    shape.SetLayer(pcbnew.Edge_Cuts)
    shape.SetWidth(pcbnew.FromMM(width_mm))
    shape.SetArcGeometry(mm_point(*start), mm_point(*mid), mm_point(*end))
    shape.SetFilled(False)
    board.Add(shape)


def build_outline(
    board_path: Path,
    radius_mm: float,
    flex_length_mm: float,
    flex_width_mm: float,
    left_center_mm: tuple[float, float],
    line_width_mm: float,
) -> tuple[float, float, float, float]:
    board = pcbnew.LoadBoard(str(board_path))
    removed = remove_existing_edge_cuts(board)

    if flex_width_mm >= 2 * radius_mm:
        raise ValueError("Flex width must be smaller than the rigid circle diameter")
    if flex_length_mm <= 0:
        raise ValueError("Flex length must be positive")

    left_x, center_y = left_center_mm
    center_gap_mm = 2 * radius_mm + flex_length_mm
    right_x = left_x + center_gap_mm

    half_width = flex_width_mm / 2.0
    half_chord = math.sqrt(radius_mm * radius_mm - half_width * half_width)

    left_upper = (left_x + half_chord, center_y - half_width)
    left_lower = (left_x + half_chord, center_y + half_width)
    right_upper = (right_x - half_chord, center_y - half_width)
    right_lower = (right_x - half_chord, center_y + half_width)

    left_outer = (left_x - radius_mm, center_y)
    right_outer = (right_x + radius_mm, center_y)

    # Walk the perimeter clockwise: left outer arc, lower flex edge,
    # right outer arc, then the upper flex edge back to the start.
    add_arc(board, left_upper, left_outer, left_lower, line_width_mm)
    add_segment(board, left_lower, right_lower, line_width_mm)
    add_arc(board, right_lower, right_outer, right_upper, line_width_mm)
    add_segment(board, right_upper, left_upper, line_width_mm)

    pcbnew.SaveBoard(str(board_path), board)

    overall_width_mm = 2 * radius_mm + center_gap_mm
    overall_height_mm = 2 * radius_mm
    print(f"board: {board_path}")
    print(f"removed existing Edge.Cuts items: {removed}")
    print(f"center gap: {center_gap_mm:.3f} mm")
    print(f"flex width: {flex_width_mm:.3f} mm")
    print(
        "bounding box: "
        f"{overall_width_mm:.3f} x {overall_height_mm:.3f} mm"
    )

    return (
        center_gap_mm,
        flex_width_mm,
        overall_width_mm,
        overall_height_mm,
    )


def parse_point(value: str) -> tuple[float, float]:
    try:
        x_text, y_text = value.split(",", 1)
        return float(x_text), float(y_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("point must be formatted as X,Y") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    parser.add_argument("--radius", type=float, default=5.5)
    parser.add_argument("--flex-length", type=float, default=2.0)
    parser.add_argument("--flex-width", type=float, default=5.0)
    parser.add_argument("--left-center", type=parse_point, default=(100.0, 100.0))
    parser.add_argument("--line-width", type=float, default=0.05)
    args = parser.parse_args()

    board_path = args.board.resolve()
    if not board_path.is_file():
        raise SystemExit(f"board file not found: {board_path}")

    build_outline(
        board_path=board_path,
        radius_mm=args.radius,
        flex_length_mm=args.flex_length,
        flex_width_mm=args.flex_width,
        left_center_mm=args.left_center,
        line_width_mm=args.line_width,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
