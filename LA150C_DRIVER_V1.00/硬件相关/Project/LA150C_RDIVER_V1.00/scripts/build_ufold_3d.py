"""Build the LA150C rigid-flex U-fold 3D model (STEP) + section illustration.

Fold specification (2026-10-09, rev B):
  * Developed FPC span          : 104.898979 .. 110.101020 mm (5.202041 mm)
  * Bend band                   : 4.0 mm wide, i.e. bend lines at 2.0 mm
                                  either side of the FPC centre
                                  -> x = 105.5 and x = 109.5 (flat layout)
  * Bend radius (neutral axis)  : R = 0.5 mm, FPC thickness 0.2 mm
  * Fold                        : 180 deg U-turn, 90 deg arc + flat + 90 deg arc
  * Layer stack                 : bottom copper on the OUTSIDE (convex) of the
                                  bend, top copper on the INSIDE (concave)
  * Rigid thickness             : 0.6 mm both hard regions

Folded geometry:
  * flat flex tail next to each rigid board : 0.601 mm
  * straight section at the bottom of the U : 2.429 mm
  * mid-plane separation of the two boards  : 2R + 2.429 = 3.429 mm

The component 3D bodies are taken straight out of KiCad
(``kicad-cli pcb export step --no-board-body``) so the STEP carries both the
folded rigid-flex board and the placed components.
"""

import math
import os
import subprocess
import tempfile

import FreeCAD
import Import
import Part
from PIL import Image, ImageDraw, ImageFont


PROJECT = (
    r"D:\办公相关\项目相关\三花\03-灵巧手项目\O-硬件设计"
    r"\LA150C_DRIVER_V1.00\硬件相关\Project\LA150C_RDIVER_V1.00"
)
PCB = os.path.join(PROJECT, "LA150C_RDIVER_V1.00_rigid_flex_Ufold_marked.kicad_pcb")
KICAD_CLI = r"D:\KiCad10.0\bin\kicad-cli.exe"
OUT_DIR = os.path.join(PROJECT, "generated")
STEP_OUT = os.path.join(OUT_DIR, "LA150C_RDIVER_rigid_flex_Ufold.step")
PNG_OUT = os.path.join(OUT_DIR, "LA150C_RDIVER_rigid_flex_Ufold_illustration.png")
COMP_STEP = os.path.join(tempfile.gettempdir(), "la150c_ufold_components.step")

RIGID_T = 0.6
FLEX_T = 0.2
FLEX_WIDTH = 5.0
Y_CENTER = 100.0

X_FLEX_A = 104.898979          # flex edge of board A (near magnet, left in flat)
X_FLEX_C = 110.101020          # flex edge of board C (far magnet, right in flat)
FLEX_LEN = X_FLEX_C - X_FLEX_A
FPC_CENTER = 0.5 * (X_FLEX_A + X_FLEX_C)     # 107.5, also the fold axis in X

BEND_HALF = 2.0                # bend lines at FPC centre +/- 2.0 mm
R_BEND = 0.5                   # neutral-axis bend radius
ARC_LEN = math.pi * R_BEND / 2.0
MID_STRAIGHT = 2.0 * BEND_HALF - 2.0 * ARC_LEN
FLAT_END = (FLEX_LEN - 2.0 * BEND_HALF) / 2.0
SEP = 2.0 * R_BEND + MID_STRAIGHT

X_BEND = X_FLEX_C - FLAT_END   # 109.5, fold line nearest board C in flat layout
C1Z = SEP - R_BEND             # upper arc centre
C2Z = R_BEND                   # lower arc centre

# kicad-cli exports the board bottom at z = 0; its modelled body is 0.51 thick
# while the design stackup is 0.6.  Align the components on the mid-plane.
EXPORT_MID = 0.255


def v(x, y=0.0, z=0.0):
    return FreeCAD.Vector(x, y, z)


def arc(p1, pm, p2):
    return Part.Arc(v(*p1), v(*pm), v(*p2)).toShape()


def line(p1, p2):
    return Part.makeLine(v(*p1), v(*p2))


def font(size):
    for path in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def board_a_edges():
    """Board A (near magnet) outline from the final PCB Edge.Cuts."""
    return [
        arc((96.012, 96.212405), (100.0, 94.5), (104.898979, 97.5)),
        line((96.012, 103.78759), (96.012, 96.212405)),
        arc((104.898979, 102.5), (100.0, 105.5), (96.012, 103.78759)),
        line((104.898979, 102.5), (104.898979, 97.5)),
    ]


def board_c_edges():
    """Board C (far magnet) outline from the final PCB Edge.Cuts."""
    return [
        arc((110.101020, 97.5), (115.0, 94.5), (118.9924, 96.217046)),
        line((118.9924, 96.217046), (118.9924, 103.782952)),
        arc((118.9924, 103.782952), (115.0, 105.5), (110.101020, 102.5)),
        line((110.101020, 102.5), (110.101020, 97.5)),
    ]


# M0.5 edge notches on board A, wire-solder holes on board C.
A_NOTCHES = [(97.4267, 95.4938, 0.275), (102.5967, 104.4485, 0.275)]
C_HOLES = [
    (113.022010, 96.158010, 0.609600),
    (114.522000, 95.758000, 0.610355),
    (116.021986, 95.758070, 0.591699),
    (117.421990, 96.258070, 0.588972),
]


def make_plate(edges, holes, z0, z1):
    plate = Part.Face(Part.Wire(edges)).extrude(v(0, 0, z1 - z0))
    for cx, cy, r in holes:
        plate = plate.cut(
            Part.makeCylinder(r, (z1 - z0) + 2.0, v(cx, cy, z0 - 1.0), v(0, 0, 1))
        )
    return plate


def flex_surface(offset, step=18):
    """Flex surface polyline in the x-z plane.

    offset = +FLEX_T/2 -> outside of the bend (convex)
    offset = -FLEX_T/2 -> inside of the bend (concave)
    """
    rr = R_BEND + offset
    pts = [(X_FLEX_C, SEP + offset), (X_BEND, SEP + offset)]
    for i in range(step + 1):
        a = math.radians(90.0 + 90.0 * i / step)
        pts.append((X_BEND + rr * math.cos(a), C1Z + rr * math.sin(a)))
    pts.append((X_BEND - rr, C2Z))
    for i in range(step + 1):
        a = math.radians(180.0 + 90.0 * i / step)
        pts.append((X_BEND + rr * math.cos(a), C2Z + rr * math.sin(a)))
    pts.append((X_FLEX_C, -offset))
    return pts


def make_flex():
    """C-shaped 0.2 mm flex made of 90 deg arc + straight + 90 deg arc."""
    ro = R_BEND + FLEX_T / 2.0      # outer surface radius 0.6
    ri = R_BEND - FLEX_T / 2.0      # inner surface radius 0.4
    x_out = X_BEND - ro             # 108.9
    x_in = X_BEND - ri              # 109.1
    z_top = SEP
    z_bot = 0.0
    half = FLEX_T / 2.0
    s2 = math.sqrt(0.5)

    edges = [
        line((X_FLEX_C, 0.0, z_top + half), (X_BEND, 0.0, z_top + half)),
        arc((X_BEND, 0.0, z_top + half),
            (X_BEND - ro * s2, 0.0, C1Z + ro * s2),
            (x_out, 0.0, C1Z)),
        line((x_out, 0.0, C1Z), (x_out, 0.0, C2Z)),
        arc((x_out, 0.0, C2Z),
            (X_BEND - ro * s2, 0.0, C2Z - ro * s2),
            (X_BEND, 0.0, z_bot - half)),
        line((X_BEND, 0.0, z_bot - half), (X_FLEX_C, 0.0, z_bot - half)),
        line((X_FLEX_C, 0.0, z_bot - half), (X_FLEX_C, 0.0, z_bot + half)),
        line((X_FLEX_C, 0.0, z_bot + half), (X_BEND, 0.0, z_bot + half)),
        arc((X_BEND, 0.0, z_bot + half),
            (X_BEND - ri * s2, 0.0, C2Z - ri * s2),
            (x_in, 0.0, C2Z)),
        line((x_in, 0.0, C2Z), (x_in, 0.0, C1Z)),
        arc((x_in, 0.0, C1Z),
            (X_BEND - ri * s2, 0.0, C1Z + ri * s2),
            (X_BEND, 0.0, z_top - half)),
        line((X_BEND, 0.0, z_top - half), (X_FLEX_C, 0.0, z_top - half)),
        line((X_FLEX_C, 0.0, z_top - half), (X_FLEX_C, 0.0, z_top + half)),
    ]
    flex = Part.Face(Part.Wire(edges)).extrude(v(0, FLEX_WIDTH, 0))
    flex.translate(v(0, Y_CENTER - FLEX_WIDTH / 2.0, 0))
    return flex


def make_substrate():
    plate_c = make_plate(board_c_edges(), C_HOLES, 0.0, RIGID_T)
    plate_c.translate(v(0, 0, -RIGID_T / 2.0))

    # Board A is folded 180 deg about a y-axis through the FPC centre, so its
    # bottom copper ends up facing outwards and the flex bottom copper rides
    # the convex side of the U.
    plate_a = make_plate(board_a_edges(), A_NOTCHES, 0.0, RIGID_T)
    plate_a = plate_a.mirror(v(FPC_CENTER, 0, 0), v(1, 0, 0))
    plate_a.translate(v(0, 0, SEP - RIGID_T / 2.0))

    return plate_c.fuse(plate_a).fuse(make_flex()).removeSplitter()


def export_components():
    os.makedirs(OUT_DIR, exist_ok=True)
    cmd = [
        KICAD_CLI, "pcb", "export", "step",
        "--no-board-body", "--force", "--output", COMP_STEP, PCB,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    return COMP_STEP


def load_components():
    doc = FreeCAD.newDocument("flat_components")
    Import.insert(COMP_STEP, "flat_components")
    solids, seen = [], set()
    for obj in doc.Objects:
        shape = getattr(obj, "Shape", None)
        if shape is None:
            continue
        for sol in shape.Solids:
            bb = sol.BoundBox
            if bb.XMin < 95.0:          # unplaced library copy at the origin
                continue
            key = tuple(round(getattr(bb, a), 4) for a in
                        ("XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax"))
            if key in seen:
                continue
            seen.add(key)
            solids.append(sol.copy())
    FreeCAD.closeDocument("flat_components")
    return solids


def place_components(solids):
    """Undo the KiCad y-flip and fold the board-A parts with their board."""
    placed = []
    for sol in solids:
        s = sol.mirror(v(0, 0, 0), v(0, 1, 0))    # export y -> PCB y
        if s.BoundBox.Center.x < FPC_CENTER:
            s.rotate(v(FPC_CENTER, 0, EXPORT_MID), v(0, 1, 0), 180.0)
            s.translate(v(0, 0, SEP - EXPORT_MID))
        else:
            s.translate(v(0, 0, -EXPORT_MID))
        placed.append(s)
    return placed


def draw_illustration():
    img = Image.new("RGB", (1680, 1040), "white")
    d = ImageDraw.Draw(img)
    f_title = font(28)
    f_text = font(20)
    f_small = font(17)
    f_tiny = font(15)

    d.text((46, 24), "LA150C 软硬结合板  U 型弯折（底层朝外 / 顶层朝里，含元器件）",
           fill="black", font=f_title)
    d.text((46, 62),
           f"硬板 0.6 mm  |  FPC 0.2 mm x 5.202 x 5.0  |  R=0.5 mm  |  "
           f"折弯带 4.0 mm（中心 ±2.0）  |  两板中面间距 {SEP:.3f} mm",
           fill=(60, 60, 60), font=f_text)

    # ---------- main panel: true-scale side view --------------------------
    sx = 78.0

    def px(x, z):
        return (80.0 + (x - 108.4) * sx, 900.0 - (z + 0.7) * sx)

    d.text((70, 110), "整体侧视（真实比例）", fill=(20, 20, 20), font=f_text)

    d.rectangle([px(FPC_CENTER, SEP + RIGID_T / 2), px(118.9924, SEP - RIGID_T / 2)],
                fill=(208, 208, 208), outline="black", width=2)
    d.rectangle([px(110.101020, RIGID_T / 2), px(118.9924, -RIGID_T / 2)],
                fill=(208, 208, 208), outline="black", width=2)

    d.line([px(x, z) for x, z in flex_surface(+FLEX_T / 2.0)],
           fill=(230, 140, 0), width=5, joint="curve")
    d.line([px(x, z) for x, z in flex_surface(-FLEX_T / 2.0)],
           fill=(0, 120, 200), width=5, joint="curve")

    d.text((300, 470), "硬板 A（靠磁钢）0.6 mm", fill="black", font=f_small)
    d.text((300, 902), "硬板 C（远磁钢）0.6 mm", fill="black", font=f_small)
    d.text((70, 936), "橙：FPC 底层铜 = 弯折外弧（凸面，朝外）",
           fill=(200, 110, 0), font=f_small)
    d.text((70, 968), "蓝：FPC 顶层铜 = 弯折内弧（凹面，朝里）",
           fill=(0, 105, 180), font=f_small)
    d.text((70, 1000),
           f"两板中面间距 = 2R + U 底直边 = {2 * R_BEND:.3f} + "
           f"{MID_STRAIGHT:.3f} = {SEP:.3f} mm",
           fill=(70, 70, 70), font=f_small)

    # ---------- detail panel: bend zone -----------------------------------
    zs = 190.0
    d.text((1080, 110), "弯折区放大（4 mm 折弯带）", fill=(20, 20, 20), font=f_text)
    d.text((1080, 150), "两条弯折线展开间距 4.0 mm（各距 FPC 中心 2.0 mm）",
           fill=(70, 70, 70), font=f_tiny)
    d.text((1080, 176), f"R = {R_BEND:.1f} mm（中性层）内弧 0.4 / 外弧 0.6",
           fill=(70, 70, 70), font=f_tiny)
    d.text((1080, 202),
           f"U 底直边 {MID_STRAIGHT:.3f} mm，两端平直段 {FLAT_END:.3f} mm",
           fill=(70, 70, 70), font=f_tiny)
    d.text((1080, 228), "折弯带内无元器件（元件均位于刚性区）",
           fill=(70, 70, 70), font=f_tiny)

    def qp(x, z):
        return (1080.0 + (x - 108.3) * zs, 1000.0 - (z + 0.7) * zs)

    d.rectangle([qp(FPC_CENTER, SEP + RIGID_T / 2), qp(111.4, SEP - RIGID_T / 2)],
                fill=(208, 208, 208), outline="black", width=2)
    d.rectangle([qp(110.101020, RIGID_T / 2), qp(111.4, -RIGID_T / 2)],
                fill=(208, 208, 208), outline="black", width=2)

    d.line([qp(x, z) for x, z in flex_surface(+FLEX_T / 2.0)],
           fill=(230, 140, 0), width=8, joint="curve")
    d.line([qp(x, z) for x, z in flex_surface(-FLEX_T / 2.0)],
           fill=(0, 120, 200), width=8, joint="curve")

    for cz in (C1Z, C2Z):
        cx, cy = qp(X_BEND, cz)
        d.line([(cx - 18, cy), (cx + 18, cy)], fill=(150, 150, 150), width=2)
        d.line([(cx, cy - 18), (cx, cy + 18)], fill=(150, 150, 150), width=2)

    r0 = qp(X_BEND, C1Z)
    r1 = qp(X_BEND - R_BEND, C1Z)
    d.line([r0, r1], fill=(200, 60, 60), width=2)
    d.text((r0[0] + 8, r0[1] - 8), "R0.5", fill=(200, 60, 60), font=f_tiny)

    img.save(PNG_OUT)
    print(PNG_OUT)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    substrate = make_substrate()
    export_components()
    solids = load_components()
    placed = place_components(solids)
    compound = Part.makeCompound([substrate] + placed)

    print("substrate valid:", substrate.isValid(), "volume %.4f" % substrate.Volume)
    print("component solids:", len(placed))
    for s in placed:
        bb = s.BoundBox
        print("  x=[%8.3f,%8.3f] y=[%8.3f,%8.3f] z=[%7.3f,%7.3f]"
              % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
    bb = compound.BoundBox
    print("total bbox x=[%.4f, %.4f] y=[%.4f, %.4f] z=[%.4f, %.4f]"
          % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
    print("flex len=%.4f  bend band=%.1f  R=%.2f  flat=%.4f  mid=%.4f  sep=%.4f"
          % (FLEX_LEN, 2 * BEND_HALF, R_BEND, FLAT_END, MID_STRAIGHT, SEP))

    doc = FreeCAD.newDocument("ufold")
    obj = doc.addObject("Part::Feature", "LA150C_RDIVER_rigid_flex_Ufold")
    obj.Shape = compound
    doc.recompute()
    Import.export([obj], STEP_OUT)
    print(STEP_OUT)

    draw_illustration()


main()
