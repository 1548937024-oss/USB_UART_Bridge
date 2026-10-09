"""Drop the rigid-flex U-fold board into the KZ11 structure assembly.

Removes the original three-board stack (LA150三板_20261007 / 08 / 09) from
0101-0007#电控部分结构-LA150C-KZ11-20261008.STEP and places the folded
rigid-flex board into the freed space.

Placement undoes the transform that was used to build the flat PCB layout out
of this assembly:

    assembly --rotate +45 deg about Z--> shift --mirror Y--> PCB

so the model goes back with translate(-centre) -> mirror Y -> rotate(+45).
Z is chosen so board A keeps its original mid-plane, which preserves the
magnet-to-sensor air gap of the stack.
"""

import os
import math

import FreeCAD
import Import
import Part


BASE = (
    r"D:\办公相关\项目相关\三花\03-灵巧手项目\O-硬件设计"
    r"\LA150C_DRIVER_V1.00"
)
STRUCTURE = os.path.join(
    BASE, "结构相关", "0101-0007#电控部分结构-LA150C-KZ11-20261008.STEP"
)
RIGID_FLEX = os.path.join(
    BASE,
    "硬件相关", "Project", "LA150C_RDIVER_V1.00", "generated",
    "LA150C_RDIVER_rigid_flex_Ufold.step",
)
OUT = os.path.join(BASE, "结构相关", "LA150C_KZ11_rigid_flex_assembly.step")

# Volumes of the three original board solids inside the flattened assembly.
BOARD_SOLID_VOLUMES = (5.326, 226.865, 119.372)
VOL_TOL = 0.05

PCB_CENTER = (115.0, 100.0)         # folded board centre in PCB coordinates
BOARD_A_TOP_PCB = 3.729204          # board A magnet-side face in the model
BOARD_A_TOP_ASSEMBLY = -17.330480   # board A magnet-side face in the structure

# Wire-solder holes of board C, used as a placement cross-check.
C_HOLES_PCB = [
    (113.022010, 96.158010),
    (114.522000, 95.758000),
    (116.021986, 95.758070),
    (117.421990, 96.258070),
]
C_HOLES_ASSEMBLY = [
    (-0.9192, 4.1719),
    (-2.2627, 3.5355),
    (-3.3234, 2.4749),
    (-4.1012, 1.1314),
]


def is_board_solid(solid):
    return any(abs(solid.Volume - v) < VOL_TOL for v in BOARD_SOLID_VOLUMES)


def place_board(shape):
    dz = BOARD_A_TOP_ASSEMBLY - BOARD_A_TOP_PCB
    shape.translate(FreeCAD.Vector(-PCB_CENTER[0], -PCB_CENTER[1], 0))
    shape = shape.mirror(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0))
    shape.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), 45.0)
    shape.translate(FreeCAD.Vector(0, 0, dz))
    return shape, dz


def main():
    doc = FreeCAD.newDocument("kz11")
    Import.insert(STRUCTURE, "kz11")
    doc.recompute()

    top = None
    for obj in doc.Objects:
        if obj.TypeId == "App::Part" and "0101-0007" in obj.Label:
            top = obj
    if top is None:
        raise RuntimeError("top assembly 0101-0007 not found")

    solids = list(top.Shape.Solids)
    keep = [s for s in solids if not is_board_solid(s)]
    dropped = sorted(round(s.Volume, 3) for s in solids if is_board_solid(s))
    print("board solids removed:", dropped, "| kept %d of %d" % (len(keep), len(solids)))

    board_doc = FreeCAD.newDocument("rigid_flex")
    Import.insert(RIGID_FLEX, "rigid_flex")
    board_doc.recompute()
    candidates = [o for o in board_doc.Objects
                  if getattr(o, "Shape", None) is not None and o.Shape.Solids]
    board = max(candidates, key=lambda o: len(o.Shape.Solids)).Shape.copy()
    print("rigid-flex solids:", len(board.Solids))

    board, dz = place_board(board)
    print("dz = %.4f" % dz)

    for (px, py), (ax, ay) in zip(C_HOLES_PCB, reversed(C_HOLES_ASSEMBLY)):
        ux = px - PCB_CENTER[0]
        uy = -(py - PCB_CENTER[1])
        c, s = math.cos(math.radians(45.0)), math.sin(math.radians(45.0))
        vx, vy = c * ux - s * uy, s * ux + c * uy
        print("  C hole pcb(%.3f,%.3f) -> assembly(%.3f,%.3f)  expect(%.4f,%.4f)"
              % (px, py, vx, vy, ax, ay))

    bb = board.BoundBox
    print("board bbox x=[%.3f,%.3f] y=[%.3f,%.3f] z=[%.3f,%.3f]"
          % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))

    out = FreeCAD.newDocument("out")
    structure = out.addObject("Part::Feature", "KZ11_structure_no_driver_boards")
    structure.Shape = Part.makeCompound(keep)
    placed = out.addObject("Part::Feature", "LA150C_rigid_flex_Ufold")
    placed.Shape = board
    out.recompute()

    Import.export([structure, placed], OUT)
    print(OUT)


main()
