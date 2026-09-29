#!/usr/bin/env python3
"""Build the MicroDriver V2.10 POWER sheet.

Block order follows PRJ_MicroDriver_V2.10.pdf page 1:
input protection (D4 TVS + MOS1 reverse-polarity PMOS), bus capacitors,
the U2 MPM3572 buck with its feedback network, the VBUS divider and the
U3 TLV74333 3.3 V LDO with the power LED.

Rules applied (docs/V2.10_绘制规则.md):
  * one PWR_FLAG per net;
  * every branch that lands mid-wire gets a junction;
  * pin coordinates come from the library, never from a guessed transform;
  * protection parts sit on the protected side of the series element.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "MicroDriver_V2.10"
ROOT_UUID = k.make_uuid("root", PROJECT_NAME)
STEM = "SCH_MicroDriver_V2.10_POWER"

P = PROJECT_NAME


def main() -> int:
    lib = PROJECT_ROOT / "library" / f"{PROJECT_NAME}.kicad_sym"
    libraries = k.Libraries()
    libraries.register("power", lib)
    libraries.register(PROJECT_NAME, lib)
    libraries.register("Device", Path(r"D:\KiCad10.0\share\kicad\symbols\Device.kicad_sym"))
    libraries.register("Transistor_FET", Path(r"D:\KiCad10.0\share\kicad\symbols\Transistor_FET.kicad_sym"))

    sheet = k.Sheet(
        path=PROJECT_ROOT / f"{STEM}.kicad_sch",
        project=PROJECT_NAME,
        uuid_key=STEM,
        libraries=libraries,
        root_uuid=ROOT_UUID,
        sheet_uuid=k.make_uuid("sheet", STEM),
        power_base=300,
        flag_base=200,
        power_rotation=180,
    )

    sheet.text("title", "MicroDriver V2.10 - POWER\nVBUS_IN → 保护 → VBUS → MPM3572 降压 → 5V → TLV74333 → 3.3V", 20.32, 17.78, 1.5)

    # start well clear of the manually numbered #PWRxx references above
    pwr = 300

    def gnd(x, y):
        nonlocal pwr
        pwr += 1
        sheet.power("power:GND_POWER_GROUND", f"#PWR{pwr:02d}", x, y)

    # ---------------------------------------------------------------- block A
    # input protection: VBUS_IN -> D4 (TVS to EGND) -> MOS1 -> VBUS
    sheet.block("INPUT PROTECTION", 19.05, 26.67, 129.54, 88.9)
    sheet.power("power:VBUS_IN_BAR", "#PWR01", 26.67, 33.02)
    sheet.junction(26.67, 38.1)
    sheet.pwr_flag(26.67, 38.1)

    # D4: bidirectional TVS, placed vertically (rot 90) from VBUS_IN to earth
    sheet.component(f"{P}:SMBJ58CA", "D4", "SMBJ58CA", 38.1, 55.88, rotation=90,
                    footprint="", description="双向 TVS 58V/600W SMB")
    # rot 90 puts pin 1 at the bottom and pin 2 at the top
    d4_hi = sheet.pin(f"{P}:SMBJ58CA", 38.1, 55.88, 90, "2")
    d4_lo = sheet.pin(f"{P}:SMBJ58CA", 38.1, 55.88, 90, "1")
    sheet.power("power:EGND_EARTH", "#PWR02", d4_lo[0], d4_lo[1] + 5.08)
    sheet.wire(d4_lo[0], d4_lo[1], d4_lo[0], d4_lo[1] + 5.08)
    sheet.junction(d4_lo[0], d4_lo[1] + 5.08)
    sheet.pwr_flag(d4_lo[0], d4_lo[1] + 5.08)
    sheet.text("note:d4", "D4: SMBJ58CA 双向，钳位 93.6V", 25.4, 81.28)

    # MOS1: high-side PMOS reverse-polarity protection, source on the input side
    sheet.component("Transistor_FET:Q_PMOS_GSD", "MOS1", "PMOS", 55.88, 45.72,
                    rotation=270, footprint="", description="-100V/-1.2A/280mΩ SOT23")
    mos_s = sheet.pin("Transistor_FET:Q_PMOS_GSD", 55.88, 45.72, 270, "2")
    mos_d = sheet.pin("Transistor_FET:Q_PMOS_GSD", 55.88, 45.72, 270, "3")
    mos_g = sheet.pin("Transistor_FET:Q_PMOS_GSD", 55.88, 45.72, 270, "1")
    node_y = mos_s[1]
    # VBUS_IN -> source, with the TVS tapping the same node
    sheet.wire(26.67, 33.02, 26.67, node_y)
    sheet.wire(26.67, node_y, mos_s[0], node_y)
    # d4_hi already lands on the VBUS_IN node run, so only a junction is needed
    sheet.junction(d4_hi[0], node_y)
    # drain -> VBUS
    sheet.wire(mos_d[0], mos_d[1], 78.74, node_y)
    sheet.power("power:VBUS_BAR", "#PWR03", 78.74, node_y)
    # gate pull-down
    sheet.component("Device:R", "R14", "10K", 55.88, 29.21, footprint="",
                    description="0201 10K 1%")
    r14_bot = sheet.pin("Device:R", 55.88, 29.21, 0, "2")
    r14_top = sheet.pin("Device:R", 55.88, 29.21, 0, "1")
    sheet.wire(mos_g[0], mos_g[1], r14_bot[0], r14_bot[1])
    sheet.wire(r14_top[0], r14_top[1], r14_top[0], r14_top[1] - 5.08)
    gnd(r14_top[0], r14_top[1] - 5.08)
    # C19: 100nF gate-source snubber for MOS1 (sits next to R14 in the original)
    c19_x = mos_s[0] - 5.08
    sheet.component("Device:C", "C19", "100nF", c19_x, (mos_g[1] + mos_s[1]) / 2,
                    footprint="", description="0402 100nF 50V 栅源缓冲")
    c19_a = sheet.pin("Device:C", c19_x, (mos_g[1] + mos_s[1]) / 2, 0, "1")
    c19_b = sheet.pin("Device:C", c19_x, (mos_g[1] + mos_s[1]) / 2, 0, "2")
    sheet.wire(mos_g[0], mos_g[1], c19_a[0], mos_g[1])
    # c19_a already sits on mos_g's y, so no extra stub is needed
    sheet.wire(c19_b[0], mos_s[1], mos_s[0], mos_s[1])
    # c19_b lands in the middle of the VBUS_IN node run
    sheet.junction(c19_b[0], mos_s[1])
    sheet.text("note:mos", "MOS1: PMOS 反接保护；栅极经 R14 下拉", 25.4, 86.36)

    # ---------------------------------------------------------------- block B
    # bus capacitors on the protected VBUS rail
    sheet.block("BUS CAPACITORS", 134.62, 26.67, 264.16, 88.9)
    sheet.wire(139.7, 38.1, 259.08, 38.1)
    sheet.wire(139.7, 38.1, 139.7, 43.18)
    sheet.power("power:VBUS_BAR", "#PWR04", 139.7, 38.1)
    # C14 is the VBUS-EGND leg of the common-mode (Y) capacitor pair;
    # C18 is the GND-EGND leg and is added separately below.
    caps = [
        ("C14", "2.2nF", "1206 2.2nF 630V", 149.86, "EGND"),
        ("C15", "100nF", "0603 100nF 100V", 165.1, "GND"),
        ("C16", "10uF", "1210 10uF 100V", 180.34, "GND"),
        ("C17", "10uF", "1210 10uF 100V", 195.58, "GND"),
        ("C22", "10uF", "1210 10uF 100V", 210.82, "GND"),
        ("C23", "100nF", "0603 100nF 100V", 226.06, "GND"),
    ]
    sheet.wire(259.08, 38.1, 259.08, 43.18)
    for ref, value, desc, x, ret in caps:
        sheet.component("Device:C", ref, value, x, 49.53, footprint="", description=desc)
        sheet.wire(x, 38.1, x, 45.72)
        sheet.junction(x, 38.1)
        sheet.wire(x, 53.34, x, 58.42)
        if ret == "EGND":
            sheet.power("power:EGND_EARTH", f"#PWR1{pwr:02d}", x, 58.42)
            pwr += 1
        else:
            gnd(x, 58.42)

    # C18: common-mode (Y) capacitor from GND to EGND
    c18_x = 241.3
    sheet.component("Device:C", "C18", "2.2nF", c18_x, 73.66, footprint="",
                    description="1206 2.2nF 630V 共模 Y 电容")
    c18_a = sheet.pin("Device:C", c18_x, 73.66, 0, "1")
    c18_b = sheet.pin("Device:C", c18_x, 73.66, 0, "2")
    sheet.wire(226.06, 58.42, c18_x, 58.42)
    sheet.junction(226.06, 58.42)
    sheet.wire(c18_x, 58.42, c18_a[0], c18_a[1])
    sheet.wire(c18_b[0], c18_b[1], c18_b[0], c18_b[1] + 5.08)
    sheet.power("power:EGND_EARTH", "#PWR05", c18_b[0], c18_b[1] + 5.08)
    sheet.text("note:bus", "共模 Y 电容：C14 跨 VBUS-EGND，C18 跨 GND-EGND（2.2nF 630V）；C15/C16/C17/C22/C23 接 GND", 139.7, 86.36)

    # ---------------------------------------------------------------- block C
    # U2 MPM3572 buck and its feedback network
    sheet.block("BUCK 5V - U2 MPM3572", 19.05, 96.52, 179.07, 162.56)
    u2 = f"{P}:MPM3572"
    u2_x, u2_y = 76.2, 124.46
    sheet.component(u2, "U2", "MPM3572", u2_x, u2_y, footprint="",
                    description="80V/0.6A 电源模块 LGA-6x6")

    def u2pin(n):
        return sheet.pin(u2, u2_x, u2_y, 0, n)

    bus_x = 43.18                      # left-hand VBUS rail
    out_x = 111.76                     # right-hand 5V rail
    gnd_rail = 152.4

    # VBUS rail feeds VIN (23/24) and EN (1)
    sheet.power("power:VBUS_BAR", "#PWR30", bus_x, 109.22)
    sheet.wire(bus_x, 109.22, bus_x, 123.19)
    for pin_number in ("23", "24", "1"):
        px, py = u2pin(pin_number)
        sheet.wire(bus_x, py, px, py)
        sheet.junction(bus_x, py)

    # FREQ (6) tied to GND per datasheet default 400 kHz
    fx, fy = u2pin("6")
    sheet.wire(fx, fy, bus_x - 5.08, fy)
    sheet.wire(bus_x - 5.08, fy, bus_x - 5.08, gnd_rail)
    gnd(bus_x - 5.08, gnd_rail)

    # 5V rail: a horizontal run above the OUT pins, with the two output
    # capacitors hanging below it so no wire crosses a capacitor pin.
    out7, out8 = u2pin("7"), u2pin("8")
    rail_y5 = out7[1] - 2.54
    rail_end = 142.24
    sheet.power("power:+5V_BAR", "#PWR31", out_x, rail_y5)
    sheet.wire(out7[0], rail_y5, rail_end, rail_y5)
    sheet.junction(out_x, rail_y5)
    sheet.wire(out7[0], rail_y5, out8[0], out8[1])
    sheet.junction(out7[0], out7[1])

    # output capacitors, placed below the rail
    for ref, value, desc, x in (("C20", "10uF", "0603 10uF 6.3V", 127.0),
                                ("C21", "100nF", "0201 100nF 16V", 142.24)):
        cy = rail_y5 + 7.62
        sheet.component("Device:C", ref, value, x, cy, footprint="", description=desc)
        top = sheet.pin("Device:C", x, cy, 0, "1")
        bot = sheet.pin("Device:C", x, cy, 0, "2")
        sheet.wire(x, rail_y5, top[0], top[1])
        sheet.junction(x, rail_y5)
        sheet.wire(bot[0], bot[1], bot[0], gnd_rail)
        gnd(bot[0], gnd_rail)

    # module ground pins (9-12, 20-22, AGND 5) to one rail
    bottom_pins = [u2pin(n) for n in ("9", "10", "11", "12", "20", "21", "22", "5")]
    gy = bottom_pins[0][1] + 5.08
    for px, py in bottom_pins:
        sheet.wire(px, py, px, gy)
        sheet.junction(px, gy)
    sheet.wire(bottom_pins[0][0], gy, bottom_pins[-1][0], gy)
    gnd(bottom_pins[0][0], gy)
    sheet.junction(bottom_pins[0][0], gy)

    # feedback divider: 5V -> R15 -> FB -> R16 -> GND
    fx0 = 157.48
    sheet.component("Device:R", "R15", "15K", fx0, 104.14, footprint="",
                    description="0402 15K 1%")
    sheet.component("Device:R", "R16", "26.1K", fx0, 114.3, footprint="",
                    description="0201 26.1K 0.5%")
    r15a = sheet.pin("Device:R", fx0, 104.14, 0, "1")
    r15b = sheet.pin("Device:R", fx0, 104.14, 0, "2")
    r16a = sheet.pin("Device:R", fx0, 114.3, 0, "1")
    r16b = sheet.pin("Device:R", fx0, 114.3, 0, "2")
    sheet.wire(r15a[0], r15a[1], r15a[0], r15a[1] - 5.08)
    sheet.power("power:+5V_BAR", "#PWR32", r15a[0], r15a[1] - 5.08)
    sheet.wire(r15b[0], r15b[1], r16a[0], r16a[1])
    sheet.junction(r15b[0], r15b[1])
    sheet.wire(r15b[0], r15b[1], 147.32, r15b[1])
    sheet.wire(147.32, r15b[1], 147.32, 128.27)
    fbx, fby = u2pin("4")
    sheet.wire(147.32, 128.27, fbx, fby)
    sheet.wire(r16b[0], r16b[1], r16b[0], r16b[1] + 5.08)
    gnd(r16b[0], r16b[1] + 5.08)

    # BST (17) bootstrap return to SW (15) as recommended by the datasheet
    bst = u2pin("17")
    sw = u2pin("15")
    sheet.wire(bst[0], bst[1], bst[0] + 5.08, bst[1])
    sheet.wire(bst[0] + 5.08, bst[1], bst[0] + 5.08, sw[1])
    sheet.wire(bst[0] + 5.08, sw[1], sw[0], sw[1])
    sheet.junction(sw[0], sw[1])
    # the audit reports BST landing mid-wire; pin it explicitly
    sheet.junction(bst[0], bst[1])
    sheet.text("note:fb", "R15/R16 为 U2 反馈分压；FREQ 接 GND=400kHz 默认；BST 经内部电容到 SW", 25.4, 160.02)

    # ---------------------------------------------------------------- block D
    # VBUS divider -> AD-VBUS
    sheet.block("VBUS MONITOR", 19.05, 170.18, 127.0, 205.74)
    r19_x, r20_x, c24_x = 30.48, 30.48, 45.72
    sheet.component("Device:R", "R19", "100K", r19_x, 184.15, footprint="",
                    description="0402 100K 1%")
    sheet.component("Device:R", "R20", "4.7K", r20_x, 196.85, footprint="",
                    description="0201 4.7K 1%")
    sheet.component("Device:C", "C24", "100pF", c24_x, 196.85, footprint="",
                    description="0201 100pF 50V")
    r19_a = sheet.pin("Device:R", r19_x, 184.15, 0, "1")
    r19_b = sheet.pin("Device:R", r19_x, 184.15, 0, "2")
    r20_a = sheet.pin("Device:R", r20_x, 196.85, 0, "1")
    r20_b = sheet.pin("Device:R", r20_x, 196.85, 0, "2")
    c24_a = sheet.pin("Device:C", c24_x, 196.85, 0, "1")
    c24_b = sheet.pin("Device:C", c24_x, 196.85, 0, "2")
    tap_y = (r19_b[1] + r20_a[1]) / 2
    sheet.power("power:VBUS_BAR", "#PWR40", r19_a[0], r19_a[1] - 5.08)
    sheet.wire(r19_a[0], r19_a[1] - 5.08, r19_a[0], r19_a[1])
    # divider mid-point is the sense node
    sheet.wire(r19_b[0], r19_b[1], r20_a[0], r20_a[1])
    sheet.junction(r19_b[0], tap_y)
    sheet.wire(r19_b[0], tap_y, c24_x, tap_y)
    sheet.junction(c24_x, tap_y)
    sheet.wire(c24_x, tap_y, c24_a[0], c24_a[1])
    sheet.hier_label("AD-VBUS", c24_x + 25.4, tap_y, shape="output", rotation=0)
    sheet.wire(c24_x, tap_y, c24_x + 25.4, tap_y)
    # shared ground
    gy2 = c24_b[1] + 5.08
    sheet.wire(r20_b[0], r20_b[1], r20_b[0], gy2)
    sheet.wire(c24_b[0], c24_b[1], c24_b[0], gy2)
    sheet.wire(r20_b[0], gy2, c24_b[0], gy2)
    gnd(r20_b[0], gy2)
    sheet.text("note:div", "分压比 4.7/(100+4.7)=1/22.28；C24 100pF，需与固件标定核对", 25.4, 176.53)

    # ---------------------------------------------------------------- block E
    # U3 LDO -> 3.3V and the power LED
    sheet.block("LDO 3.3V - U3 TLV74333", 134.62, 170.18, 274.32, 205.74)
    u3 = f"{P}:TLV74333PDBVR"
    u3_x, u3_y = 172.72, 187.96
    sheet.component(u3, "U3", "TLV74333PDBVR", u3_x, u3_y, rotation=0,
                    footprint="", description="3.3V/300mA LDO SOT-23-5")

    def u3pin(n):
        return sheet.pin(u3, u3_x, u3_y, 0, n)

    in_pin = u3pin("1")
    en_pin = u3pin("3")
    gnd_pin = u3pin("2")
    out_pin = u3pin("5")
    led_rail = 213.36

    # +5V feeds IN and EN
    sheet.power("power:+5V_BAR", "#PWR50", in_pin[0] - 20.32, in_pin[1])
    sheet.wire(in_pin[0] - 20.32, in_pin[1], in_pin[0], in_pin[1])
    sheet.wire(in_pin[0] - 20.32, in_pin[1], in_pin[0] - 20.32, en_pin[1])
    sheet.wire(in_pin[0] - 20.32, en_pin[1], en_pin[0], en_pin[1])
    sheet.junction(in_pin[0] - 20.32, in_pin[1])
    # input capacitors C25 / C26
    for ref, value, desc, x in (("C25", "1uF", "0402 1uF 10V", in_pin[0] - 12.7),
                                ("C26", "100nF", "0201 100nF 16V", in_pin[0] - 7.62)):
        sheet.component("Device:C", ref, value, x, in_pin[1] + 6.35, footprint="", description=desc)
        top = sheet.pin("Device:C", x, in_pin[1] + 6.35, 0, "1")
        bot = sheet.pin("Device:C", x, in_pin[1] + 6.35, 0, "2")
        sheet.wire(x, in_pin[1], top[0], top[1])
        sheet.junction(x, in_pin[1])
        sheet.wire(bot[0], bot[1], bot[0], bot[1] + 5.08)
        gnd(bot[0], bot[1] + 5.08)
    # LDO ground
    sheet.wire(gnd_pin[0], gnd_pin[1], gnd_pin[0] - 5.08, gnd_pin[1])
    sheet.wire(gnd_pin[0] - 5.08, gnd_pin[1], gnd_pin[0] - 5.08, gnd_pin[1] + 10.16)
    gnd(gnd_pin[0] - 5.08, gnd_pin[1] + 10.16)

    # 3.3V output rail with C27 / C28, then the power LED
    sheet.wire(out_pin[0], out_pin[1], led_rail, out_pin[1])
    sheet.power("power:+3.3V_BAR", "#PWR51", out_pin[0] + 12.7, out_pin[1])
    sheet.junction(out_pin[0] + 12.7, out_pin[1])
    for ref, value, desc, x in (("C27", "100nF", "0201 100nF 16V", out_pin[0] + 6.35),
                                ("C28", "1uF", "0402 1uF 10V", out_pin[0] + 10.16)):
        sheet.component("Device:C", ref, value, x, out_pin[1] + 6.35, footprint="", description=desc)
        top = sheet.pin("Device:C", x, out_pin[1] + 6.35, 0, "1")
        bot = sheet.pin("Device:C", x, out_pin[1] + 6.35, 0, "2")
        sheet.wire(x, out_pin[1], top[0], top[1])
        sheet.junction(x, out_pin[1])
        sheet.wire(bot[0], bot[1], bot[0], bot[1] + 5.08)
        gnd(bot[0], bot[1] + 5.08)

    # power LED: 3.3V -> R45 -> LED3 -> GND
    sheet.component("Device:R", "R45", "4.7K", 228.6, out_pin[1], rotation=90, footprint="",
                    description="0402 4.7K 1%")
    r45a = sheet.pin("Device:R", 228.6, out_pin[1], 90, "1")
    r45b = sheet.pin("Device:R", 228.6, out_pin[1], 90, "2")
    sheet.wire(out_pin[0], out_pin[1], r45a[0], r45a[1])
    sheet.component("Device:LED", "LED3", "XL-1005UGC", 241.3, out_pin[1], rotation=0,
                    footprint="", description="绿色 0402 LED")
    led_a = sheet.pin("Device:LED", 241.3, out_pin[1], 0, "1")
    led_b = sheet.pin("Device:LED", 241.3, out_pin[1], 0, "2")
    sheet.wire(r45b[0], r45b[1], led_a[0], led_a[1])
    sheet.wire(led_b[0], led_b[1], led_b[0] + 5.08, led_b[1])
    gnd(led_b[0] + 5.08, led_b[1])

    # one PWR_FLAG per rail, each placed exactly on the rail it declares
    sheet.pwr_flag(bottom_pins[0][0], gy)              # GND
    sheet.pwr_flag(78.74, node_y)                      # VBUS (after MOS1)
    sheet.pwr_flag(out_x, rail_y5)                     # +5V, on the rail run
    sheet.pwr_flag(out_pin[0] + 12.7, out_pin[1])      # +3.3V
    # U3 pin 4 is a no-connect; declare it explicitly
    nc = u3pin("4")
    sheet.no_connect(nc[0], nc[1])
    # U2 VCC (pin 3): the datasheet's internal 1uF decoupling means the pin
    # needs no external component, so it is explicitly left open.
    vcc = u2pin("3")
    sheet.no_connect(vcc[0], vcc[1])
    # SW is internally switched; tie both SW pins together so neither floats
    sw16 = u2pin("16")
    sheet.wire(sw[0], sw[1], sw16[0], sw16[1])
    sheet.write()
    print(f"wrote {sheet.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
