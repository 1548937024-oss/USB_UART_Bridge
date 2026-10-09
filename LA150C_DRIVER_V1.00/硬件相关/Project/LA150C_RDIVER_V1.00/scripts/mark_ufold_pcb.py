"""Refresh the U-fold annotations on the final rigid-flex PCB.

Fold spec 2026-10-09: bend lines at FPC centre +/-1.0 mm, R = 0.5 mm,
bottom copper on the outside of the bend, top copper on the inside.
"""

import os

import pcbnew


PROJECT = (
    r"D:\办公相关\项目相关\三花\03-灵巧手项目\O-硬件设计"
    r"\LA150C_DRIVER_V1.00\硬件相关\Project\LA150C_RDIVER_V1.00"
)
PCB = os.path.join(PROJECT, "LA150C_RDIVER_V1.00_rigid_flex_Ufold_marked.kicad_pcb")

FPC_CENTER_X = 106.5
BEND_X = (FPC_CENTER_X - 1.0, FPC_CENTER_X + 1.0)
LINE_Y0, LINE_Y1 = 96.0, 104.0


def is_our_mark(item):
    if item.GetLayer() != pcbnew.Dwgs_User:
        return False
    if isinstance(item, pcbnew.PCB_TEXT):
        t = item.GetText()
        return t.startswith("U-FOLD") or t.startswith("FPC bottom")
    if isinstance(item, pcbnew.PCB_SHAPE) and item.GetShape() == pcbnew.SHAPE_T_SEGMENT:
        sx = pcbnew.ToMM(item.GetStart().x)
        ex = pcbnew.ToMM(item.GetEnd().x)
        return abs(sx - ex) < 1e-6 and abs(sx - FPC_CENTER_X) < 1e-3
    return False


def add_line(board, x):
    line = pcbnew.PCB_SHAPE(board)
    line.SetShape(pcbnew.SHAPE_T_SEGMENT)
    line.SetStart(pcbnew.VECTOR2I_MM(x, LINE_Y0))
    line.SetEnd(pcbnew.VECTOR2I_MM(x, LINE_Y1))
    line.SetLayer(pcbnew.Dwgs_User)
    line.SetWidth(pcbnew.FromMM(0.10))
    board.Add(line)


def add_text(board, text, x, y, size=0.8):
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    item.SetLayer(pcbnew.Dwgs_User)
    item.SetTextSize(pcbnew.VECTOR2I_MM(size, size))
    item.SetTextThickness(pcbnew.FromMM(0.15))
    board.Add(item)


def main():
    board = pcbnew.LoadBoard(PCB)
    if board is None:
        raise RuntimeError("failed to load %s" % PCB)

    for item in list(board.GetDrawings()):
        if is_our_mark(item):
            board.Remove(item)

    for x in BEND_X:
        add_line(board, x)

    add_text(board, "U-FOLD 180deg  R=0.5mm  bend lines FPC centre +/-1.0mm",
             106.5, 95.36, 0.8)
    add_text(board, "FPC bottom Cu: outside (convex)   top Cu: inside (concave)",
             106.5, 105.02, 0.7)

    pcbnew.SaveBoard(PCB, board)
    print(PCB)


main()
