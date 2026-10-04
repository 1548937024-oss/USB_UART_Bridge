#!/usr/bin/env python3
"""Write the A4 drawing sheet used by this project.

The chosen format keeps the imported AD frame (double border, 1-6 / A-D zone
markings and the four corner folding marks) but replaces the large
180 x 39 mm title block with the compact 110 x 24 mm engineering block:
Title + subtitle / Rev / Date / Sheet / Size.

The original file is preserved once as ``AD_Style_A4_full.kicad_wks``.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET = PROJECT_ROOT / "AD_Style_A4.kicad_wks"
FULL_COPY = PROJECT_ROOT / "AD_Style_A4_full.kicad_wks"


def line(name: str, x1, y1, x2, y2, corner: str | None = None, width="0.35") -> k.Node:
    start: list[k.Node] = ["start", k.number(x1), k.number(y1)]
    end: list[k.Node] = ["end", k.number(x2), k.number(y2)]
    if corner:
        start.append(corner)
        end.append(corner)
    return ["line", ["name", k.quote(f"{name}:Line")], start, end, ["linewidth", width]]


def rect(name: str, x1, y1, x2, y2, corner: str | None = None, width="0.35") -> k.Node:
    start: list[k.Node] = ["start", k.number(x1), k.number(y1)]
    end: list[k.Node] = ["end", k.number(x2), k.number(y2)]
    if corner:
        start.append(corner)
        end.append(corner)
    return ["rect", ["name", k.quote(f"{name}:Rect")], start, end, ["linewidth", width]]


def tbtext(
    name: str, text: str, x: float, y: float, size: float = 1.5, justify: str = "left"
) -> k.Node:
    node: k.Node = [
        "tbtext",
        k.quote(text),
        ["name", k.quote(f"{name}:Text")],
        ["pos", k.number(x), k.number(y)],
        ["font", ["linewidth", "0.18"], ["size", k.number(size), k.number(size)]],
    ]
    if justify != "left":
        node.append(["justify", justify])
    return node


def build() -> list[k.Node]:
    root: list[k.Node] = [
        "page_layout",
        [
            "setup",
            ["textsize", "1.5", "1.5"],
            ["linewidth", "0.15"],
            ["textlinewidth", "0.15"],
            ["left_margin", "5"],
            ["right_margin", "5"],
            ["top_margin", "5"],
            ["bottom_margin", "5"],
        ],
        # --- border
        rect("rect1", -5, -5, -5, -5, corner="ltcorner"),
        rect("rect2", 0, 0, 0, 0, corner="ltcorner", width="0.7"),
        # --- zone ticks on the four edges
        line("segm1", 128.5, -5, 128.5, 0, corner="ltcorner", width="1.05"),
        line("segm2", 128.5, -5, 128.5, 0, corner="lbcorner", width="1.05"),
        line("segm3", -5, 95, 0, 95, corner="ltcorner", width="1.05"),
        line("segm4", -5, 95, 0, 95, corner="rtcorner", width="1.05"),
        line("segm5", 28.5, -5, 28.5, 0, corner="ltcorner"),
        line("segm6", 78.5, -5, 78.5, 0, corner="ltcorner"),
        line("segm7", 128.5, -5, 128.5, 0, corner="ltcorner"),
        line("segm8", 178.5, -5, 178.5, 0, corner="ltcorner"),
        line("segm9", 228.5, -5, 228.5, 0, corner="ltcorner"),
        line("segm10", 28.5, -5, 28.5, 0, corner="lbcorner"),
        line("segm11", 78.5, -5, 78.5, 0, corner="lbcorner"),
        line("segm12", 128.5, -5, 128.5, 0, corner="lbcorner"),
        line("segm13", 178.5, -5, 178.5, 0, corner="lbcorner"),
        line("segm14", 228.5, -5, 228.5, 0, corner="lbcorner"),
        line("segm15", -5, 45, 0, 45, corner="ltcorner"),
        line("segm16", -5, 95, 0, 95, corner="ltcorner"),
        line("segm17", -5, 145, 0, 145, corner="ltcorner"),
        line("segm18", -5, 45, 0, 45, corner="rtcorner"),
        line("segm19", -5, 95, 0, 95, corner="rtcorner"),
        line("segm20", -5, 145, 0, 145, corner="rtcorner"),
        # --- zone labels
        tbtext("text1", "1", 3.5, -2.5, 3.5, "center"),
        tbtext("text2", "2", 53.5, -2.5, 3.5, "center"),
        tbtext("text3", "3", 103.5, -2.5, 3.5, "center"),
        tbtext("text4", "4", 153.5, -2.5, 3.5, "center"),
        tbtext("text5", "5", 203.5, -2.5, 3.5, "center"),
        tbtext("text6", "6", 253.5, -2.5, 3.5, "center"),
        tbtext("text11", "A4", 253.5, -2.5, 3.5, "center"),
        tbtext("text7", "A", -2.5, 20, 3.5, "center"),
        tbtext("text8", "B", -2.5, 70, 3.5, "center"),
        tbtext("text9", "C", -2.5, 120, 3.5, "center"),
        tbtext("text10", "D", -2.5, 170, 3.5, "center"),
        # --- slim title block: 90 x 20 mm in the bottom-right corner
        rect("rect3", 0, 0, 90, 20, width="0.5"),
        line("segm41", 0, 10, 90, 10),
        line("segm42", 18, 10, 18, 0),
        line("segm43", 45, 10, 45, 0),
        line("segm44", 68, 10, 68, 0),
        tbtext("text42", "Title", 2, 15.5, 1.5),
        tbtext("text43", "%C1", 13, 15, 2.0),
        tbtext("text44", "Rev", 1, 6.5, 1.5),
        tbtext("text45", "%R", 9, 6, 2.0),
        tbtext("text46", "Date", 19, 6.5, 1.5),
        tbtext("text47", "%D", 28, 6, 2.0),
        tbtext("text48", "Sheet", 46, 6.5, 1.5),
        tbtext("text49", "%S/%N", 57, 6, 2.0),
        tbtext("text50", "Size", 69, 6.5, 1.5),
        tbtext("text51", "%Z", 78, 6, 2.0),
    ]
    return root


def compact_title_block() -> list[k.Node]:
    return [
        rect("rect3", 0, 0, 110, 24, width="0.5"),
        line("segm41", 0, 12, 110, 12),
        line("segm42", 22, 12, 22, 0),
        line("segm43", 56, 12, 56, 0),
        line("segm44", 86, 12, 86, 0),
        tbtext("text40", "Title", 55, 21.5, 1.2, "center"),
        tbtext("text42", "%T", 55, 18.5, 2.0, "center"),
        tbtext("text43", "%C0", 55, 14.5, 1.2, "center"),
        tbtext("text44", "Rev", 11, 9.5, 1.1, "center"),
        tbtext("text45", "%R", 11, 5.0, 1.7, "center"),
        tbtext("text46", "Date", 39, 9.5, 1.1, "center"),
        tbtext("text47", "%D", 39, 5.0, 1.7, "center"),
        tbtext("text48", "Sheet", 71, 9.5, 1.1, "center"),
        tbtext("text49", "%S/%N", 71, 5.0, 1.7, "center"),
        tbtext("text50", "Size", 98, 9.5, 1.1, "center"),
        tbtext("text51", "%Z", 98, 5.0, 1.7, "center"),
    ]


def full_ad_border() -> list[k.Node]:
    root = k.Parser(FULL_COPY.read_text(encoding="utf-8")).parse()
    if not root or root[0] != "page_layout":
        raise ValueError(f"Not a page layout: {FULL_COPY}")
    for index, node in enumerate(root):
        if isinstance(node, list) and node and node[0] == "rect":
            name = node[1]
            if (
                isinstance(name, list)
                and name[0] == "name"
                and "rect3" in k.atom(name[1])
            ):
                return root[1:index]
    raise RuntimeError("rect3 not found in the full AD drawing sheet")


def build_selected() -> list[k.Node]:
    return ["page_layout", *full_ad_border(), *compact_title_block()]


def main() -> int:
    if TARGET.is_file() and not FULL_COPY.is_file():
        shutil.copy2(TARGET, FULL_COPY)
    TARGET.write_text(
        k.serialize(build_selected(), level=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {TARGET.name} (AD frame + compact 110 x 24 mm title block)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
