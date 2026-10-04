#!/usr/bin/env python3
"""Check the exported PDF: page identity and text staying inside the frame."""

from __future__ import annotations

import sys
from pathlib import Path

import pdfplumber

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF = PROJECT_ROOT / "docs" / "LA150C_RDIVER_V1.00.pdf"
MARGIN = 8.0  # mm; the AD style A4 sheet frame starts 5 mm from the edge


def main() -> int:
    problems: list[str] = []
    with pdfplumber.open(PDF) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            width_mm = page.width / 72 * 25.4
            height_mm = page.height / 72 * 25.4
            words = page.extract_words(use_text_flow=True)
            title = " ".join(w["text"] for w in words[:6])
            print(f"page {index}: {width_mm:.0f}x{height_mm:.0f} mm | {title[:70]}")
            for word in words:
                x0 = word["x0"] / 72 * 25.4
                x1 = word["x1"] / 72 * 25.4
                y0 = word["top"] / 72 * 25.4
                y1 = word["bottom"] / 72 * 25.4
                # The AD style sheet puts zone letters and the title block in
                # the outer band; anything confined there is template art, not
                # schematic content.
                if min(x0, width_mm - x1, y0, height_mm - y1) < MARGIN:
                    continue
                if x0 < MARGIN or x1 > width_mm - MARGIN or y0 < MARGIN or y1 > height_mm - MARGIN:
                    problems.append(
                        f"page {index}: {word['text']!r} at "
                        f"({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f}) leaves the frame"
                    )
    if problems:
        print(f"\n{len(problems)} out-of-frame text items:")
        for line in problems[:40]:
            print("  " + line)
        return 1
    print("\nall text stays inside the drawing frame")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
