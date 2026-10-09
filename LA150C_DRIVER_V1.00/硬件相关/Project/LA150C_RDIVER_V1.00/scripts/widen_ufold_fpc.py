"""Widen the rigid-flex FPC of the final PCB from 3.202 mm to 5.202 mm.

Fold spec 2026-10-09 (rev B): the bend band grows from 2.0 mm to 4.0 mm, so
the bend lines sit 2.0 mm either side of the developed FPC centre.  Board A
(near magnet) keeps its coordinates; board C (far magnet), its Edge.Cuts and
its footprints move +2.0 mm in X.  The two FPC edges are extended to match.

Point probing is done from shape start/end/centre rather than getBoundingBox,
because pcbnew returns the full-circle bounding box for arcs.

The script is idempotent: on a board that already carries the widened FPC it
only re-writes the Dwgs.User annotations.
"""

import os

import pcbnew


PROJECT = (
    r"D:\办公相关\项目相关\三花\03-灵巧手项目\O-硬件设计"
    r"\LA150C_DRIVER_V1.00\硬件相关\Project\LA150C_RDIVER_V1.00"
)
PCB = os.path.join(PROJECT, "LA150C_RDIVER_V1.00_rigid_flex_Ufold_marked.kicad_pcb")

SHIFT = 2.0
X_FLEX_A = 104.898979
X_C_OLD = 108.101020
X_C_NEW = X_C_OLD + SHIFT                 # 110.101020
FPC_CENTER = 0.5 * (X_FLEX_A + X_C_NEW)   # 107.5
BEND_HALF = 2.0
Y0, Y1 = 97.5, 102.5                      # FPC band in Y
TOL = 1e-3


def mm(pt):
    return pcbnew.ToMM(pt.x), pcbnew.ToMM(pt.y)


def probe_points(item):
    shape = item.GetShape()
    if shape == pcbnew.SHAPE_T_CIRCLE:
        return [mm(item.GetCenter())]
    pts = [mm(item.GetStart()), mm(item.GetEnd())]
    if shape == pcbnew.SHAPE_T_ARC:
        try:
            pts.append(mm(item.GetArcMid()))
        except Exception:
            pass
    return pts


def already_widened(board):
    for item in board.GetDrawings():
        if item.GetLayer() != pcbnew.Edge_Cuts:
            continue
        if item.GetShape() != pcbnew.SHAPE_T_SEGMENT:
            continue
        for pt in (mm(item.GetStart()), mm(item.GetEnd())):
            if abs(pt[0] - X_C_NEW) < TOL:
                return True
    return False


def extend_fpc_edge(item):
    for getter, setter in ((item.GetStart, item.SetStart), (item.GetEnd, item.SetEnd)):
        x, y = mm(getter())
        if abs(x - X_C_OLD) < TOL:
            setter(pcbnew.VECTOR2I_MM(X_C_NEW, y))
            return True
    return False


def widen(board):
    if already_widened(board):
        print("FPC already widened; running repair pass only")
    else:
        for item in board.GetDrawings():
            if item.GetLayer() != pcbnew.Edge_Cuts:
                continue
            xs = [pt[0] for pt in probe_points(item)]
            xmin, xmax = min(xs), max(xs)
            if xmin >= X_C_OLD - TOL:
                item.Move(pcbnew.VECTOR2I_MM(SHIFT, 0))
            elif xmin <= X_FLEX_A + TOL and xmax >= X_C_OLD - TOL:
                if not extend_fpc_edge(item):
                    raise RuntimeError("FPC edge not extended: %s" % probe_points(item))

        for fp in board.GetFootprints():
            if pcbnew.ToMM(fp.GetPosition().x) > 107.0:
                fp.Move(pcbnew.VECTOR2I_MM(SHIFT, 0))

    # Repair pass: any board-C arc still sitting on the old flex edge gets
    # moved to the new one.  No-op on a board that is already correct.
    for item in board.GetDrawings():
        if item.GetLayer() != pcbnew.Edge_Cuts:
            continue
        if item.GetShape() != pcbnew.SHAPE_T_ARC:
            continue
        xs = [pt[0] for pt in probe_points(item)]
        if min(abs(x - X_C_OLD) for x in xs) < 0.05:
            item.Move(pcbnew.VECTOR2I_MM(SHIFT, 0))
            print("repaired arc at old board-C edge")


def add_line(board, x, y0, y1, width=0.10):
    line = pcbnew.PCB_SHAPE(board)
    line.SetShape(pcbnew.SHAPE_T_SEGMENT)
    line.SetStart(pcbnew.VECTOR2I_MM(x, y0))
    line.SetEnd(pcbnew.VECTOR2I_MM(x, y1))
    line.SetLayer(pcbnew.Dwgs_User)
    line.SetWidth(pcbnew.FromMM(width))
    board.Add(line)


def add_rect(board, x0, y0, x1, y1, width=0.05):
    rect = pcbnew.PCB_SHAPE(board)
    rect.SetShape(pcbnew.SHAPE_T_RECT)
    rect.SetStart(pcbnew.VECTOR2I_MM(x0, y0))
    rect.SetEnd(pcbnew.VECTOR2I_MM(x1, y1))
    rect.SetLayer(pcbnew.Dwgs_User)
    rect.SetWidth(pcbnew.FromMM(width))
    board.Add(rect)


def add_text(board, text, x, y, size=0.8):
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    item.SetLayer(pcbnew.Dwgs_User)
    item.SetTextSize(pcbnew.VECTOR2I_MM(size, size))
    item.SetTextThickness(pcbnew.FromMM(0.15))
    board.Add(item)


def rewrite_annotations(board):
    for item in list(board.GetDrawings()):
        if item.GetLayer() == pcbnew.Dwgs_User:
            board.Remove(item)

    add_rect(board, X_FLEX_A, Y0, X_C_NEW, Y1)
    for x in (FPC_CENTER - BEND_HALF, FPC_CENTER + BEND_HALF):
        add_line(board, x, Y0 - 1.5, Y1 + 1.5)

    add_text(board, "U-FOLD 180deg  R=0.5mm  bend lines FPC centre +/-2.0mm",
             107.5, 94.20, 0.8)
    add_text(board, "FPC 0.2 mm  (5.202 x 5.0)", 107.5, 105.30, 0.8)
    add_text(board, "FPC bottom Cu: outside (convex)   top Cu: inside (concave)",
             107.5, 106.10, 0.7)
    add_text(board, "Rigid 0.6 mm", 100.4824, 93.3704, 0.8)
    add_text(board, "Rigid 0.6 mm", 115.03, 93.5228, 0.8)


def main():
    board = pcbnew.LoadBoard(PCB)
    if board is None:
        raise RuntimeError("failed to load %s" % PCB)

    widen(board)
    rewrite_annotations(board)
    pcbnew.SaveBoard(PCB, board)

    print("FPC span  %.6f .. %.6f  (length %.4f mm)"
          % (X_FLEX_A, X_C_NEW, X_C_NEW - X_FLEX_A))
    print("fold lines %.1f and %.1f" % (FPC_CENTER - BEND_HALF, FPC_CENTER + BEND_HALF))
    print(PCB)


main()
