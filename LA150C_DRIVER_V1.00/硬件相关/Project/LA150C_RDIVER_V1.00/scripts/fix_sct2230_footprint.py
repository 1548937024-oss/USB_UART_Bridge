"""Replace U1 on the final rigid-flex PCB with the ECLGA2.5X1.7-7L footprint.

The board previously carried a Qorvo DFN-8 2x2 mm land pattern, which has the
wrong pin count (8 vs 7), the wrong body size (2.0x2.0 vs 2.5x1.7), the wrong
pad row spacing (2.0 mm vs 1.75 mm) and two overlapping thermal pads.
"""

import os

import pcbnew

PROJECT = (
    r"D:\办公相关\项目相关\三花\03-灵巧手项目\O-硬件设计"
    r"\LA150C_DRIVER_V1.00\硬件相关\Project\LA150C_RDIVER_V1.00"
)
PCB = os.path.join(PROJECT, "LA150C_RDIVER_V1.00_rigid_flex_Ufold_marked.kicad_pcb")
LIB = os.path.join(PROJECT, "library", "LA150C_RDIVER_V1.00.pretty")
FP_NAME = "ECLGA2.5X1.7-7L"
LIB_NICK = "LA150C_RDIVER_V1.00"


def main():
    board = pcbnew.LoadBoard(PCB)
    if board is None:
        raise RuntimeError("failed to load %s" % PCB)

    old = None
    for fp in board.GetFootprints():
        if str(fp.GetReference()) == "U1":
            old = fp
            break
    if old is None:
        raise RuntimeError("U1 not found")

    position = old.GetPosition()
    orientation = old.GetOrientation()
    value = old.GetValue()

    new = pcbnew.FootprintLoad(LIB, FP_NAME)
    if new is None:
        raise RuntimeError("footprint %s not found in %s" % (FP_NAME, LIB))

    board.Remove(old)
    board.Add(new)
    new.SetPosition(position)
    new.SetOrientation(orientation)
    new.SetReference("U1")
    new.SetValue(value)
    new.SetFPID(pcbnew.LIB_ID(LIB_NICK, FP_NAME))

    # The rest of this board hides the reference / value text on the silkscreen.
    new.Reference().SetVisible(False)
    new.Value().SetVisible(False)

    pcbnew.SaveBoard(PCB, board)

    pads = sorted((str(p.GetNumber()), pcbnew.ToMM(p.GetPosition().x),
                   pcbnew.ToMM(p.GetPosition().y),
                   pcbnew.ToMM(p.GetSize().x), pcbnew.ToMM(p.GetSize().y))
                  for p in new.Pads())
    print("U1 ->", FP_NAME, "at", pcbnew.ToMM(position.x), pcbnew.ToMM(position.y))
    for num, x, y, w, h in pads:
        print("  pad %-2s x=%8.3f y=%8.3f  %.2f x %.2f" % (num, x, y, w, h))
    print(PCB)


main()
