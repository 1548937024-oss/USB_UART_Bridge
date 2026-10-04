#!/usr/bin/env python3
"""Geometry audit over the generated LA150C sheets.

ERC proves connectivity; it says nothing about whether a wire runs through a
symbol body or whether two symbol bodies overlap.  This script re-reads the
generated ``.kicad_sch`` files and checks, for every placed symbol:

* the symbol body stays inside the A4 page frame;
* no other symbol body overlaps it (power symbols and test points excluded);
* no wire passes through the body interior.

It is the machine-checkable part of the visual review.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "LA150C_RDIVER_V1.00"
LIBRARY = PROJECT_ROOT / "library" / f"{PROJECT_NAME}.kicad_sym"

# A4 in mm, with the drawing frame margin.
PAGE = (0.0, 0.0, 297.0, 210.0)
FRAME = (5.0, 5.0, 292.0, 205.0)

IGNORE_OVERLAP = {"TestPoint"}

# The A4 drawing sheet owns this region for its slim title block (90 x 20 mm
# anchored to the bottom-right corner); content placed here would be drawn on
# top of it.
TITLE_BLOCK = (197.0, 185.0, 300.0, 210.0)


def transform_point(x, y, rotation, mirror, lx, ly):
    if mirror == "x":
        lx = -lx
    elif mirror == "y":
        ly = -ly
    radians = math.radians(rotation)
    rx = lx * math.cos(radians) - ly * math.sin(radians)
    ry = lx * math.sin(radians) + ly * math.cos(radians)
    return x + rx, y - ry


def local_bbox(definition):
    xs: list[float] = []
    ys: list[float] = []

    def walk(node):
        if not isinstance(node, list):
            return
        if node and node[0] in ("rectangle", "polyline", "circle"):
            for item in node:
                if isinstance(item, list) and item and item[0] in ("start", "end", "center"):
                    xs.append(float(k.atom(item[1])))
                    ys.append(float(k.atom(item[2])))
                if isinstance(item, list) and item and item[0] == "pts":
                    for point in item[1:]:
                        xs.append(float(k.atom(point[1])))
                        ys.append(float(k.atom(point[2])))
        for item in node:
            if isinstance(item, list):
                walk(item)

    walk(definition)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def inside(inner, outer):
    return (
        inner[0] >= outer[0] - 1e-6
        and inner[1] >= outer[1] - 1e-6
        and inner[2] <= outer[2] + 1e-6
        and inner[3] <= outer[3] + 1e-6
    )


def overlaps(a, b, slack=1e-6):
    return not (
        a[2] <= b[0] + slack
        or b[2] <= a[0] + slack
        or a[3] <= b[1] + slack
        or b[3] <= a[1] + slack
    )


def segment_hits_box(p1, p2, box, skip):
    """True when the segment passes through the box interior."""
    x1, y1 = p1
    x2, y2 = p2
    x_lo, y_lo, x_hi, y_hi = box
    steps = max(2, int(max(abs(x2 - x1), abs(y2 - y1)) / 0.5) + 1)
    for index in range(steps + 1):
        t = index / steps
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t
        if skip and (abs(x - skip[0]) < 0.6 and abs(y - skip[1]) < 0.6):
            continue
        if x_lo + 0.05 < x < x_hi - 0.05 and y_lo + 0.05 < y < y_hi - 0.05:
            return True
    return False


def text_box(x: float, y: float, value: str, size: float = 1.27):
    """Approximate the rendered box of a left/bottom justified text."""
    width = 0.0
    for char in value:
        width += size if ord(char) > 0x2000 else size * 0.62
    return (x, y - size * 1.2, x + width, y)


def text_boxes(source):
    """Reference / Value fields and standalone texts, with their boxes."""
    root = k.Parser(source).parse()
    boxes = []
    for item in root[1:]:
        if not isinstance(item, list) or not item:
            continue
        if item[0] == "text":
            at = k.direct(item, "at")
            if at is None:
                continue
            value = k.atom(item[1])
            size = 1.27
            effects = k.direct(item, "effects")
            if effects is not None:
                font = k.direct(effects, "font")
                if font is not None:
                    sizes = k.direct(font, "size")
                    if sizes is not None:
                        size = float(k.atom(sizes[1]))
            for line_index, line in enumerate(value.split("\\n")):
                # multi-line text grows upwards from the anchor
                boxes.append(
                    (
                        f"text:{value[:12]}",
                        text_box(
                            float(k.atom(at[1])),
                            float(k.atom(at[2])) - line_index * size * 1.6,
                            line,
                            size,
                        ),
                    )
                )
        elif item[0] == "symbol":
            for prop in k.direct_all(item, "property"):
                if k.atom(prop[1]) not in ("Reference", "Value"):
                    continue
                if k.direct(prop, "hide") is not None:
                    continue
                at = k.direct(prop, "at")
                if at is None:
                    continue
                boxes.append(
                    (
                        f"{k.atom(prop[1])}:{k.atom(prop[2])}",
                        text_box(
                            float(k.atom(at[1])),
                            float(k.atom(at[2])),
                            k.atom(prop[2]),
                        ),
                    )
                )
    return boxes


def placed_symbols(source):
    root = k.Parser(source).parse()
    symbols = []
    for item in root[1:]:
        if not (isinstance(item, list) and item and item[0] == "symbol"):
            continue
        lib_id_node = k.direct(item, "lib_id")
        at_node = k.direct(item, "at")
        if lib_id_node is None or at_node is None:
            continue
        lib_id = k.atom(lib_id_node[1])
        rotation = float(k.atom(at_node[3])) if len(at_node) >= 4 else 0.0
        mirror_node = k.direct(item, "mirror")
        mirror = k.atom(mirror_node[1]) if mirror_node is not None else None
        reference = ""
        for prop in k.direct_all(item, "property"):
            if k.atom(prop[1]) == "Reference":
                reference = k.atom(prop[2])
        symbols.append(
            {
                "lib_id": lib_id,
                "x": float(k.atom(at_node[1])),
                "y": float(k.atom(at_node[2])),
                "rotation": rotation,
                "mirror": mirror,
                "reference": reference,
            }
        )
    return symbols


def extract(source, kind):
    root = k.Parser(source).parse()
    out = []
    for item in root[1:]:
        if isinstance(item, list) and item and item[0] == kind:
            out.append(item)
    return out


def main() -> int:
    library = k.read_library(LIBRARY)
    failures: list[str] = []
    for path in sorted(PROJECT_ROOT.glob("*.kicad_sch")):
        source = path.read_text(encoding="utf-8")
        symbol_nodes = {}
        for item in extract(source, "symbol"):
            at = k.direct(item, "at")
            lib = k.direct(item, "lib_id")
            if at is None or lib is None:
                continue
            symbol_nodes[len(symbol_nodes)] = item

        placed = []
        for entry in placed_symbols(source):
            lib_id = entry["lib_id"]
            name = lib_id.split(":", 1)[-1]
            definition = library.get(name)
            if definition is None:
                continue
            box = local_bbox(definition)
            if box is None:
                continue
            corners = [
                transform_point(entry["x"], entry["y"], entry["rotation"], entry["mirror"], lx, ly)
                for lx, ly in (
                    (box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])
                )
            ]
            placed.append(
                {
                    "ref": entry["reference"],
                    "name": name,
                    "box": (
                        min(c[0] for c in corners),
                        min(c[1] for c in corners),
                        max(c[0] for c in corners),
                        max(c[1] for c in corners),
                    ),
                }
            )

        # 1. inside the frame
        for entry in placed:
            if not inside(entry["box"], FRAME):
                failures.append(
                    f"{path.name}: {entry['ref']} ({entry['name']}) body {tuple(round(v, 1) for v in entry['box'])} leaves the A4 frame"
                )

        # 2. symbol bodies must not overlap
        real = [e for e in placed if not e["ref"].startswith("#") and e["name"] not in IGNORE_OVERLAP]
        for index, a in enumerate(real):
            for b in real[index + 1:]:
                if overlaps(a["box"], b["box"]):
                    failures.append(
                        f"{path.name}: {a['ref']} {tuple(round(v, 1) for v in a['box'])} overlaps {b['ref']} {tuple(round(v, 1) for v in b['box'])}"
                    )

        # 3. no wire through a body
        wires = []
        for wire in extract(source, "wire"):
            pts = k.direct(wire, "pts")
            if pts is None or len(pts) < 3:
                continue
            wires.append(
                (
                    (float(k.atom(pts[1][1])), float(k.atom(pts[1][2]))),
                    (float(k.atom(pts[2][1])), float(k.atom(pts[2][2]))),
                )
            )
        for entry in real:
            for p1, p2 in wires:
                if segment_hits_box(p1, p2, entry["box"], skip=(entry["box"][0], entry["box"][1])):
                    failures.append(
                        f"{path.name}: wire {p1} -> {p2} crosses {entry['ref']} ({entry['name']}) body {tuple(round(v, 1) for v in entry['box'])}"
                    )

        # 4. every drawn anchor stays inside the frame
        anchors: list[tuple[str, float, float]] = []
        for point in extract(source, "junction"):
            at = k.direct(point, "at")
            anchors.append(("junction", float(k.atom(at[1])), float(k.atom(at[2]))))
        for point in extract(source, "no_connect"):
            at = k.direct(point, "at")
            anchors.append(("no_connect", float(k.atom(at[1])), float(k.atom(at[2]))))
        for kind in ("label", "global_label", "hierarchical_label"):
            for item in extract(source, kind):
                at = k.direct(item, "at")
                anchors.append((kind, float(k.atom(at[1])), float(k.atom(at[2]))))
        for item in extract(source, "text"):
            at = k.direct(item, "at")
            anchors.append(("text", float(k.atom(at[1])), float(k.atom(at[2]))))
        for p1, p2 in wires:
            anchors.append(("wire", p1[0], p1[1]))
            anchors.append(("wire", p2[0], p2[1]))
        for kind, x, y in anchors:
            if not (FRAME[0] <= x <= FRAME[2] and FRAME[1] <= y <= FRAME[3]):
                failures.append(
                    f"{path.name}: {kind} anchor ({x}, {y}) leaves the A4 frame"
                )
            elif (
                TITLE_BLOCK[0] <= x <= TITLE_BLOCK[2]
                and TITLE_BLOCK[1] <= y <= TITLE_BLOCK[3]
            ):
                failures.append(
                    f"{path.name}: {kind} anchor ({x}, {y}) lands on the drawing "
                    f"sheet title block"
                )

        # 5. Reference / Value / note text boxes must not overlap
        boxes = text_boxes(source)
        for index in range(len(boxes)):
            name_a, box_a = boxes[index]
            for name_b, box_b in boxes[index + 1:]:
                if name_a == name_b:
                    continue
                if overlaps(box_a, box_b, slack=0.15):
                    failures.append(
                        f"{path.name}: text {name_a!r} {tuple(round(v, 1) for v in box_a)} "
                        f"overlaps {name_b!r} {tuple(round(v, 1) for v in box_b)}"
                    )

        print(f"{path.name}: {len(placed)} symbols, {len(wires)} wires checked")

    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for line in failures:
            print("  " + line)
        return 1
    print("\nno geometry problems found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
