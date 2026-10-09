"""Build the SCT2230MLUAR 3D body (ECLGA2.5X1.7-7L).

Model frame follows KiCad's 3D convention for a front-side footprint:
model +x = footprint +x, model +y = footprint -y (up), model +z = out of board.

Package: 2.50 x 1.70 mm body, 1.25 mm total height, 7 lands 0.75 x 0.25 mm at
0.5 mm pitch plus a 0.75 x 1.20 mm exposed thermal pad.
"""

import os

import FreeCAD
import Import
import Part


OUT = (
    r"D:\办公相关\项目相关\三花\03-灵巧手项目\O-硬件设计"
    r"\LA150C_DRIVER_V1.00\硬件相关\Project\LA150C_RDIVER_V1.00"
    r"\3dmodels\SCT2230MLUAR.step"
)

BODY_W = 2.50
BODY_D = 1.70
BODY_TOP = 1.25
LAND_T = 0.03
PAD_W = 0.65          # long axis, along x
PAD_D = 0.25          # width, along y
EP_W = 0.65
EP_D = 1.20

# (x, y) in model coordinates; y is up, i.e. the mirror of the footprint +y.
LANDS = [
    (0.875, 0.50),    # 1 VOUT
    (-0.875, 0.75),   # 2 FB
    (-0.875, 0.25),   # 3 EN
    (-0.875, -0.25),  # 4 BST
    (-0.875, -0.75),  # 5 SW
    (0.875, -0.50),   # 6 VIN
    (0.875, 0.00),    # 7 PGND
]


def box(x, y, z, dx, dy, dz):
    return Part.makeBox(dx, dy, dz, FreeCAD.Vector(x, y, z))


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    solids = [
        box(-BODY_W / 2.0, -BODY_D / 2.0, LAND_T, BODY_W, BODY_D, BODY_TOP - LAND_T)
    ]
    for x, y in LANDS:
        solids.append(box(x - PAD_W / 2.0, y - PAD_D / 2.0, 0.0, PAD_W, PAD_D, LAND_T))
    solids.append(box(-EP_W / 2.0, -EP_D / 2.0, 0.0, EP_W, EP_D, LAND_T))

    fused = solids[0]
    for s in solids[1:]:
        fused = fused.fuse(s)
    fused = fused.removeSplitter()

    doc = FreeCAD.newDocument("sct2230")
    obj = doc.addObject("Part::Feature", "SCT2230MLUAR")
    obj.Shape = fused
    doc.recompute()
    Import.export([obj], OUT)

    bb = fused.BoundBox
    print("volume %.4f mm^3" % fused.Volume)
    print("bbox x=[%.3f,%.3f] y=[%.3f,%.3f] z=[%.3f,%.3f]"
          % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
    print("solids", len(fused.Solids), "valid", fused.isValid())
    print(OUT)


main()
