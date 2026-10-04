#!/usr/bin/env python3
"""Render several candidate title-block formats for the A4 drawing sheet.

The schematic content is not touched.  Each candidate is a standalone
``.kicad_wks`` file and a cropped PNG preview rendered with the same project
title-block data, so the user can pick a format before it is made the project
default.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_sheet_template as bst  # noqa: E402
import kicad_lib as k  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_DIR = PROJECT_ROOT / "docs" / "title_block_variants"
PREVIEW_DIR = TARGET_DIR / "preview"


def _title_block_nodes() -> list[k.Node]:
    return [
        "title_block",
        ["title", k.quote("LA150C RDIVER V1.00")],
        ["date", k.quote("2026-10-04")],
        ["rev", k.quote("V1.00")],
        ["company", k.quote("三花智控")],
        ["comment", "1", k.quote("LA150C 集成驱动器原理图")],
        ["comment", "2", k.quote("LA150C-RDIVER-SCH-001")],
        ["comment", "3", k.quote("设计图纸")],
        ["comment", "4", k.quote("评审通过")],
        ["comment", "5", k.quote("蒋工")],
        ["comment", "6", k.quote("待定")],
        ["comment", "7", k.quote("硬件设计部")],
    ]


def _border() -> list[k.Node]:
    base = bst.build()
    for index, node in enumerate(base):
        if isinstance(node, list) and node and node[0] == "rect":
            name = node[1]
            if isinstance(name, list) and name[0] == "name" and "rect3" in k.atom(name[1]):
                return base[:index]
    raise RuntimeError("rect3 not found in the base drawing sheet")


def _full_ad_border() -> list[k.Node]:
    """Return the full AD frame without its large title block."""
    full = PROJECT_ROOT / "AD_Style_A4_full.kicad_wks"
    root = k.Parser(full.read_text(encoding="utf-8")).parse()
    if not root or root[0] != "page_layout":
        raise ValueError(f"Not a page layout: {full}")
    for index, node in enumerate(root):
        if isinstance(node, list) and node and node[0] == "rect":
            name = node[1]
            if isinstance(name, list) and name[0] == "name" and "rect3" in k.atom(name[1]):
                return root[1:index]
    raise RuntimeError("rect3 not found in the full AD drawing sheet")


def _variant_slim() -> list[k.Node]:
    return [
        bst.rect("rect3", 0, 0, 90, 20, width="0.5"),
        bst.line("segm41", 0, 10, 90, 10),
        bst.line("segm42", 18, 10, 18, 0),
        bst.line("segm43", 45, 10, 45, 0),
        bst.line("segm44", 68, 10, 68, 0),
        bst.tbtext("text40", "Title", 9, 18.5, 1.0, "center"),
        bst.tbtext("text42", "%T", 54, 16.0, 1.8, "center"),
        bst.tbtext("text43", "%C0", 54, 12.0, 1.2, "center"),
        bst.tbtext("text44", "Rev", 9, 7.5, 1.1, "center"),
        bst.tbtext("text45", "%R", 9, 3.5, 1.7, "center"),
        bst.tbtext("text46", "Date", 31.5, 7.5, 1.1, "center"),
        bst.tbtext("text47", "%D", 31.5, 3.5, 1.7, "center"),
        bst.tbtext("text48", "Sheet", 56.5, 7.5, 1.1, "center"),
        bst.tbtext("text49", "%S/%N", 56.5, 3.5, 1.7, "center"),
        bst.tbtext("text50", "Size", 79, 7.5, 1.1, "center"),
        bst.tbtext("text51", "%Z", 79, 3.5, 1.7, "center"),
    ]


def _variant_compact() -> list[k.Node]:
    return [
        bst.rect("rect3", 0, 0, 110, 24, width="0.5"),
        bst.line("segm41", 0, 12, 110, 12),
        bst.line("segm42", 22, 12, 22, 0),
        bst.line("segm43", 56, 12, 56, 0),
        bst.line("segm44", 86, 12, 86, 0),
        bst.tbtext("text40", "Title", 55, 21.5, 1.2, "center"),
        bst.tbtext("text42", "%T", 55, 18.5, 2.0, "center"),
        bst.tbtext("text43", "%C0", 55, 14.5, 1.2, "center"),
        bst.tbtext("text44", "Rev", 11, 9.5, 1.1, "center"),
        bst.tbtext("text45", "%R", 11, 5.0, 1.7, "center"),
        bst.tbtext("text46", "Date", 39, 9.5, 1.1, "center"),
        bst.tbtext("text47", "%D", 39, 5.0, 1.7, "center"),
        bst.tbtext("text48", "Sheet", 71, 9.5, 1.1, "center"),
        bst.tbtext("text49", "%S/%N", 71, 5.0, 1.7, "center"),
        bst.tbtext("text50", "Size", 98, 9.5, 1.1, "center"),
        bst.tbtext("text51", "%Z", 98, 5.0, 1.7, "center"),
    ]


def _variant_engineering() -> list[k.Node]:
    return [
        bst.rect("rect3", 0, 0, 150, 30, width="0.5"),
        bst.line("segm41", 0, 20, 150, 20),
        bst.line("segm42", 0, 10, 150, 10),
        bst.line("segm43", 30, 20, 30, 10),
        bst.line("segm44", 60, 20, 60, 10),
        bst.line("segm45", 90, 20, 90, 10),
        bst.line("segm49", 120, 20, 120, 10),
        bst.line("segm46", 15, 10, 15, 0),
        bst.line("segm47", 40, 10, 40, 0),
        bst.line("segm48", 65, 10, 65, 0),
        bst.tbtext("text40", "Title", 75, 27.0, 1.2, "center"),
        bst.tbtext("text42", "%T", 75, 23.5, 2.4, "center"),
        bst.tbtext("text43", "%C0", 75, 21.0, 1.1, "center"),
        bst.tbtext("text44", "Rev", 15, 16.5, 1.1, "center"),
        bst.tbtext("text45", "%R", 15, 12.0, 1.7, "center"),
        bst.tbtext("text46", "Date", 45, 16.5, 1.1, "center"),
        bst.tbtext("text47", "%D", 45, 12.0, 1.7, "center"),
        bst.tbtext("text48", "Sheet", 75, 16.5, 1.1, "center"),
        bst.tbtext("text49", "%S/%N", 75, 12.0, 1.7, "center"),
        bst.tbtext("text50", "Size", 105, 16.5, 1.1, "center"),
        bst.tbtext("text51", "%Z", 105, 12.0, 1.7, "center"),
        bst.tbtext("text52", "Doc No.", 135, 16.5, 1.1, "center"),
        bst.tbtext("text53", "%C1", 135, 12.0, 1.1, "center"),
        bst.tbtext("text54", "Rev", 7.5, 7.0, 1.0, "center"),
        bst.tbtext("text55", "Date", 27.5, 7.0, 1.0, "center"),
        bst.tbtext("text56", "Author", 52.5, 7.0, 1.0, "center"),
        bst.tbtext("text57", "Changes", 107.5, 7.0, 1.0, "center"),
        bst.tbtext("text58", "V1.00", 7.5, 3.0, 1.0, "center"),
        bst.tbtext("text59", "2026-10-04", 27.5, 3.0, 1.0, "center"),
        bst.tbtext("text60", "Codex", 52.5, 3.0, 1.0, "center"),
        bst.tbtext("text61", "Initial schematic set", 107.5, 3.0, 1.0, "center"),
    ]


def _write_variants() -> list[tuple[str, Path, tuple[float, float, float, float]]]:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    border = _border()
    variants = [
        ("01_slim_current", _variant_slim(), (100, 260, 110, 37)),
        ("02_compact_engineering", _variant_compact(), (90, 256, 120, 41)),
        ("03_engineering_revision", _variant_engineering(), (55, 250, 155, 47)),
    ]
    outputs: list[tuple[str, Path, tuple[float, float, float, float]]] = []
    for name, title_block, crop in variants:
        path = TARGET_DIR / f"{name}.kicad_wks"
        path.write_text(
            k.serialize(border + title_block, level=1) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        outputs.append((name, path, crop))

    full_source = PROJECT_ROOT / "AD_Style_A4_full.kicad_wks"
    full_target = TARGET_DIR / "04_ad_full.kicad_wks"
    shutil.copy2(full_source, full_target)
    outputs.append(("04_ad_full", full_target, (25, 248, 185, 49)))

    hybrid = ["page_layout", *_full_ad_border(), *_variant_compact()]
    hybrid_path = TARGET_DIR / "05_ad_frame_compact_title.kicad_wks"
    hybrid_path.write_text(
        k.serialize(hybrid, level=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    outputs.append(
        ("05_ad_frame_compact_title", hybrid_path, (90, 256, 120, 41))
    )
    return outputs


def _minimal_schematic() -> Path:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    path = PREVIEW_DIR / "title_block_preview.kicad_sch"
    root: list[k.Node] = [
        "kicad_sch",
        ["version", "20251024"],
        ["generator", k.quote("eeschema")],
        ["generator_version", k.quote("10.0")],
        ["uuid", k.quote(str(uuid.uuid4()))],
        ["paper", k.quote("A4")],
        _title_block_nodes(),
        ["lib_symbols"],
        ["sheet_instances", ["path", k.quote("/"), ["page", k.quote("1")]]],
    ]
    path.write_text(k.serialize(root, level=1) + "\n", encoding="utf-8", newline="\n")
    return path


def _mm_to_px(value: float, dpi: int = 150) -> int:
    return int(round(value * dpi / 25.4))


def _render(
    kicad_cli: Path,
    pdftoppm: Path,
    minimal_sch: Path,
    outputs: list[tuple[str, Path, tuple[float, float, float, float]]],
) -> None:
    for name, worksheet, crop in outputs:
        pdf = PREVIEW_DIR / f"{name}.pdf"
        subprocess.run(
            [
                str(kicad_cli),
                "sch",
                "export",
                "pdf",
                "--drawing-sheet",
                str(worksheet),
                "--pages",
                "1",
                "--output",
                str(pdf),
                str(minimal_sch),
            ],
            check=True,
        )

        x, y, width, height = crop
        prefix = PREVIEW_DIR / name
        subprocess.run(
            [
                str(pdftoppm),
                "-f",
                "1",
                "-l",
                "1",
                "-r",
                "150",
                "-x",
                str(_mm_to_px(x)),
                "-y",
                str(_mm_to_px(y)),
                "-W",
                str(_mm_to_px(width)),
                "-H",
                str(_mm_to_px(height)),
                "-png",
                str(pdf),
                str(prefix),
            ],
            check=True,
        )


def _write_readme(outputs: list[tuple[str, Path, tuple[float, float, float, float]]]) -> None:
    lines = [
        "# LA150C 标题栏候选格式",
        "",
        "以下文件只替换 A4 图框的右下角标题栏，不改原理图内容。",
        "",
        "| 候选 | 标题栏尺寸 | 主要字段 | 预览 |",
        "| --- | --- | --- | --- |",
        "| 01_slim_current | 90 x 20 mm | Title / Rev / Date / Sheet / Size | `preview/01_slim_current-1.png` |",
        "| 02_compact_engineering | 110 x 24 mm | Title + subtitle / Rev / Date / Sheet / Size | `preview/02_compact_engineering-1.png` |",
        "| 03_engineering_revision | 150 x 30 mm | Title + subtitle / Rev / Date / Sheet / Size / Doc No. / revision table | `preview/03_engineering_revision-1.png` |",
        "| 04_ad_full | 180 x 39 mm | 完整 AD 工程栏 + 双行修订表 | `preview/04_ad_full-1.png` |",
        "| 05_ad_frame_compact_title | AD 图框 + 110 x 24 mm 紧凑标题栏 | 保留 04 的四角折页与分区，右下角使用 02 布局 | `preview/05_ad_frame_compact_title-1.png` |",
        "",
        "预览使用同一份标题栏数据：",
        "",
        "- Title: `LA150C RDIVER V1.00`",
        "- Subtitle: `LA150C 集成驱动器原理图`",
        "- Rev: `V1.00`",
        "- Date: `2026-10-04`",
        "- Doc No.: `LA150C-RDIVER-SCH-001`",
        "",
        "已选定 `05_ad_frame_compact_title`，并同步为工程默认 `AD_Style_A4.kicad_wks`。",
    ]
    (TARGET_DIR / "README.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--kicad-cli",
        type=Path,
        default=Path(r"D:\KiCad10.0\bin\kicad-cli.exe"),
    )
    parser.add_argument(
        "--pdftoppm",
        type=Path,
        default=Path(
            r"C:\Users\15489\.cache\codex-runtimes\codex-primary-runtime"
            r"\dependencies\native\poppler\Library\bin\pdftoppm.exe"
        ),
    )
    args = parser.parse_args()

    outputs = _write_variants()
    minimal_sch = _minimal_schematic()
    _render(args.kicad_cli, args.pdftoppm, minimal_sch, outputs)
    _write_readme(outputs)
    for name, path, _ in outputs:
        print(f"{name}: {path}")
    print(f"previews: {PREVIEW_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
