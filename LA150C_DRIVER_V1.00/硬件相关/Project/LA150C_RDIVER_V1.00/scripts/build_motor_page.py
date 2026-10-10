#!/usr/bin/env python3
"""Build the LA150C MOTOR sheet: three-phase power stage + sensing.

Blocks, from hardware design doc §3.3 / §3.4 / §3.6:

* A  三相功率级 MP6543HGL-Z (QFN-24) with the VBUS rail, input capacitors,
     V3P3 bypass + ferrite to PWR_3V3A, VCP bootstrap capacitor and the
     nFAULT pull-up / RC;
* B  三相电流采样: per phase R_up = R_dn = 8.06k to PWR_3V3A / AGND,
     100R series + 100pF to the ADC;
* C  电机温度检测 NTC (NCP15XH103F03RC) with NTC pull-up and 6.8k to ground.

Datasheet correction carried into the drawing: SA/SB/SC are the motor phase
outputs.  The 8.06k termination network belongs on the SOA/SOB/SOC current
sense outputs, which is where it is drawn here.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kicad_lib as k  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "LA150C_RDIVER_V1.00"
ROOT_UUID = k.make_uuid("root", PROJECT_NAME)
STEM = "SCH_LA150C_DRIVER_V1.00"
P = PROJECT_NAME


def main() -> int:
    lib = PROJECT_ROOT / "library" / f"{PROJECT_NAME}.kicad_sym"
    libraries = k.Libraries()
    libraries.register(PROJECT_NAME, lib)
    libraries.register("Device", Path(r"D:\KiCad10.0\share\kicad\symbols\Device.kicad_sym"))

    sheet = k.Sheet(
        path=PROJECT_ROOT / f"{STEM}.kicad_sch",
        project=PROJECT_NAME,
        uuid_key=STEM,
        libraries=libraries,
        root_uuid=ROOT_UUID,
        sheet_uuid=k.make_uuid("sheet", STEM),
        power_base=400,
        flag_base=400,
        power_rotation=0,
    )
    sheet.text(
        "title",
        "LA150C RDIVER V1.00 - MOTOR\nMP6543HGL-Z 三相功率级（内置 6 管 110mΩ / 电荷泵 / LDO / 双向采样放大器）",
        20.32,
        15.24,
        1.5,
    )

    pwr = 400

    def power(net: str, x: float, y: float, rotation: float = 0) -> None:
        nonlocal pwr
        pwr += 1
        sheet.power(f"{P}:{net}", f"#PWR{pwr:03d}", x, y, rotation)

    # ======================================================== A 三相功率级
    sheet.block("A  三相功率级 MP6543HGL-Z + 驱动辅助", 20.32, 24.13, 203.2, 152.4)

    u = f"{P}:MP6543HGL-Z"
    ux, uy = 76.2, 90.17
    sheet.component(u, "U4", "MP6543HGL-Z", ux, uy, footprint="", description="22V/2A 三相功率级 QFN-24")

    def up(n):
        return sheet.pin(u, ux, uy, 0, n)

    ena, enb, enc = up("1"), up("2"), up("3")
    pwma, pwmb, pwmc = up("4"), up("5"), up("6")
    ocadj, nsleep = up("17"), up("24")
    soa, sob, soc = up("23"), up("22"), up("21")
    nfault, v3p3, vcp, nc = up("20"), up("18"), up("14"), up("19")
    vin1, vin2, vinldo = up("7"), up("13"), up("16")
    sa, sb, sc = up("9"), up("10"), up("11")
    lss1, lss2, gndp, ep = up("8"), up("12"), up("15"), up("25")

    # --- control inputs -> hierarchical ports
    for net, point, shape in (
        ("PWM_A", pwma, "input"), ("PWM_B", pwmb, "input"), ("PWM_C", pwmc, "input"),
    ):
        sheet.wire(point[0], point[1], 35.56, point[1])
        sheet.hier_label(net, 35.56, point[1], shape=shape, rotation=180)
    sheet.wire(nsleep[0], nsleep[1], 35.56, nsleep[1])
    sheet.hier_label("nSLEEP", 35.56, nsleep[1], shape="input", rotation=180)
    sheet.text(
        "note:pwm",
        "ENx 由 10k 上拉到 3.3V 常使能，不由 MCU 控制；PWMx 由 MCU 三相 PWM 驱动。"
        " MP6543H 真值表 ENx=1,PWMx=1→VIN；ENx=1,PWMx=0→GND→内部互补输出。",
        22.86,
        30.48,
        1.27,
    )
    sheet.text(
        "note:ch",
        "★ MCU 引脚表 4.1 的 TIMER7 通道标注与 datasheet 不一致（PC8=CH2、PA11=CH0），已按表 27 的引脚号绘制，待固件确认",
        22.86,
        33.02,
        1.27,
    )

    # --- ENx pull-up to 3.3V, no MCU control.  Local labels keep the three
    # pull-ups outside the MP6543 body and avoid crossing the PWM rows.
    for net, point, stub_x in (
        ("EN_A_PU", ena, 53.34),
        ("EN_B_PU", enb, 50.8),
        ("EN_C_PU", enc, 48.26),
    ):
        sheet.wire(point[0], point[1], stub_x, point[1])
        sheet.label(net, stub_x, point[1], rotation=180)
    for refc, net, x, cy in (
        ("R34", "EN_A_PU", 34.29, 69.85),
        ("R35", "EN_B_PU", 38.1, 80.01),
        ("R36", "EN_C_PU", 30.48, 86.36),
    ):
        sheet.component("Device:R", refc, "10K", x, cy, footprint="",
                        description="0201 10K 1% EN pull-up to 3V3")
        top = sheet.pin("Device:R", x, cy, 0, "1")
        bottom = sheet.pin("Device:R", x, cy, 0, "2")
        power("PWR_3V3", top[0], top[1])
        sheet.wire(bottom[0], bottom[1], 45.72, bottom[1])
        sheet.label(net, 45.72, bottom[1])

    # --- OC_ADJ to PGND -> OCP typ 6.2A
    sheet.wire(ocadj[0], ocadj[1], 53.34, ocadj[1])
    sheet.wire(53.34, ocadj[1], 53.34, 110.49)
    power("PGND", 53.34, 110.49)
    sheet.text("note:oc", "OC_ADJ 接地：逐周期 OCP 阈值 4.7/6.2/8A(min/typ/max)，仅作短路兜底", 22.86, 35.56, 1.27)

    # --- VBUS rail and input capacitors
    rail_y = 69.85
    sheet.wire(45.72, rail_y, 78.74, rail_y)
    power("VBUS", 40.64, 64.77)
    sheet.wire(40.64, 64.77, 40.64, rail_y)
    sheet.wire(40.64, rail_y, 45.72, rail_y)
    for refc, val, desc, x in (
        ("C19", "1uF", "0603 1uF 50V X7R", 50.8),
        ("C20", "100nF", "0402 100nF 50V", 58.42),
    ):
        sheet.component("Device:C", refc, val, x, 73.66, footprint="", description=desc)
        top = sheet.pin("Device:C", x, 73.66, 0, "1")
        bot = sheet.pin("Device:C", x, 73.66, 0, "2")
        sheet.junction(x, rail_y)
        power("PGND", bot[0], bot[1])
    for point in (vin1, vin2, vinldo):
        sheet.wire(point[0], point[1], point[0], rail_y)
        sheet.junction(point[0], rail_y)

    # --- right hand side: short stubs with local net names
    for net, point in (
        ("SOA_RAW", soa), ("SOB_RAW", sob), ("SOC_RAW", soc),
        ("nFAULT", nfault), ("V3P3_DRV", v3p3), ("VCP_DRV", vcp),
    ):
        sheet.wire(point[0], point[1], 100.33, point[1])
        sheet.label(net, 100.33, point[1])
    sheet.no_connect(nc[0], nc[1])

    # --- V3P3 bypass + ferrite to PWR_3V3A
    sheet.wire(114.3, 110.49, 114.3, 113.03)
    sheet.label("V3P3_DRV", 114.3, 110.49)
    sheet.component("Device:C", "C21", "10uF", 114.3, 116.84, footprint="",
                    description="0603 10uF 10V X7R")
    c21_a = sheet.pin("Device:C", 114.3, 116.84, 0, "1")
    c21_b = sheet.pin("Device:C", 114.3, 116.84, 0, "2")
    sheet.wire(c21_b[0], c21_b[1], c21_b[0], 123.19)
    power("PGND", c21_b[0], 123.19)
    sheet.wire(114.3, 111.76, 119.38, 111.76)
    sheet.junction(114.3, 111.76)
    sheet.component(f"{P}:BLM15AG601SN1D", "FB1", "600R", 123.19, 111.76, rotation=90,
                    footprint="", description="0402 600Ω@100MHz 磁珠，隔离 V3P3 供 VDDA")
    fb1_a = sheet.pin(f"{P}:BLM15AG601SN1D", 123.19, 111.76, 90, "1")
    fb1_b = sheet.pin(f"{P}:BLM15AG601SN1D", 123.19, 111.76, 90, "2")
    sheet.wire(fb1_b[0], fb1_b[1], 132.08, fb1_b[1])
    power("PWR_3V3A", 132.08, 109.22)
    sheet.wire(132.08, 109.22, 132.08, fb1_b[1])
    # V3P3 is a power_out pin, but the ferrite is passive, so the isolated
    # analog rail has to be declared with its own flag.
    sheet.pwr_flag(129.54, fb1_b[1])
    sheet.junction(129.54, fb1_b[1])
    sheet.text(
        "note:v3p3",
        "V3P3（内部 LDO，3.3V/100mA，power_out）→ C21 10µF X7R → 磁珠 FB1 → PWR_3V3A 供 MCU VDDA/VREFP",
        120.65,
        133.35,
        1.27,
    )
    sheet.text(
        "note:v3p3b",
        "★ 该方案把功率级本地地噪声带入 MCU 模拟域，VDDA 零点噪声需样机实测；备选是独立 LDO 供模拟 3.3V",
        120.65,
        135.89,
        1.27,
    )

    # --- VCP bootstrap capacitor to VBUS
    sheet.wire(146.05, 110.49, 146.05, 113.03)
    sheet.label("VCP_DRV", 146.05, 110.49)
    sheet.component("Device:C", "C22", "1uF", 146.05, 116.84, footprint="", description="0402 1uF 16V X7R 电荷泵")
    c22_a = sheet.pin("Device:C", 146.05, 116.84, 0, "1")
    c22_b = sheet.pin("Device:C", 146.05, 116.84, 0, "2")
    sheet.wire(c22_b[0], c22_b[1], c22_b[0], 121.92)
    power("VBUS", c22_b[0], 121.92)
    sheet.text("note:vcp", "VCP 电荷泵：C22 1µF 到 VIN，不能悬空，容值不足会导致高边驱动电压下跌", 120.65, 138.43, 1.27)

    # --- nFAULT pull-up + RC debounce -> port
    node_y = 111.76
    sheet.wire(152.4, node_y, 172.72, node_y)
    sheet.hier_label("nFAULT", 172.72, node_y, shape="output", rotation=0)
    sheet.component("Device:R", "R22", "1K", 152.4, 107.95, footprint="", description="0201 1K 1%")
    r22_a = sheet.pin("Device:R", 152.4, 107.95, 0, "1")
    r22_b = sheet.pin("Device:R", 152.4, 107.95, 0, "2")
    power("PWR_3V3A", r22_a[0], 100.33)
    sheet.wire(r22_a[0], 100.33, r22_a[0], r22_a[1])
    sheet.junction(r22_b[0], node_y)
    sheet.component("Device:C", "C23", "100nF", 163.83, 115.57, footprint="", description="0402 100nF 16V")
    c23_a = sheet.pin("Device:C", 163.83, 115.57, 0, "1")
    c23_b = sheet.pin("Device:C", 163.83, 115.57, 0, "2")
    sheet.junction(c23_a[0], node_y)
    sheet.wire(c23_b[0], c23_b[1], c23_b[0], 121.92)
    power("AGND", c23_b[0], 121.92)
    sheet.text(
        "note:nfault",
        "nFAULT 开漏：R22 1k 上拉到 PWR_3V3A，C23 100nF 去抖（τ≈100µs，QS01 V1.1 口径）",
        120.65,
        140.97,
        1.27,
    )

    # --- motor phases and power ground
    for net, point, ty in (
        ("MOT_U", sa, 133.35), ("MOT_V", sb, 138.43), ("MOT_W", sc, 143.51),
    ):
        sheet.wire(point[0], point[1], point[0], ty)
        sheet.wire(point[0], ty, 55.88, ty)
        sheet.hier_label(net, 55.88, ty, shape="output", rotation=180)
    sheet.text("note:phase", "SA/SB/SC 为三相输出，半桥节点直连电机 U/V/W", 22.86, 100.33, 1.27)
    # LSS / GND / EP to one PGND rail
    gnd_rail = 113.03
    for point in (lss1, lss2, gndp, ep):
        sheet.wire(point[0], point[1], point[0], gnd_rail)
    sheet.wire(lss1[0], gnd_rail, ep[0], gnd_rail)
    for point in (lss2, gndp, ep):
        sheet.junction(point[0], gnd_rail)
    power("PGND", lss1[0], gnd_rail)
    sheet.junction(lss1[0], gnd_rail)
    sheet.text("note:lss", "LSS ×2 / GND / EP 直接连 PGND 平面", 22.86, 105.41, 1.27)

    # ======================================================== B 三相电流采样
    sheet.block("B  三相电流采样", 210.82, 24.13, 276.86, 152.4)
    sheet.text(
        "note:sense",
        "R_up = R_dn = 8.06kΩ，并联 4030Ω；G_CSA = 4030/4000 = 1.0075 V/A；V_zero = 1.65V",
        213.36,
        140.97,
        1.27,
    )
    sheet.text(
        "note:sense2",
        "★ datasheet：8.06k 端接网络接在 SOA/SOB/SOC 电流采样输出上；QS01/工程文档把它误写为 SA/SB/SC",
        213.36,
        143.51,
        1.27,
    )
    for index, (raw, net, res, cap) in enumerate(
        (
            ("SOA_RAW", "SO_A", "R23", "C24"),
            ("SOB_RAW", "SO_B", "R24", "C25"),
            ("SOC_RAW", "SO_C", "R25", "C26"),
        )
    ):
        base = 45.72 + index * 38.1
        node_x = 228.6
        # divider
        sheet.component("Device:R", f"R{26 + index}", "8.06K", node_x, base - 7.62,
                        footprint="", description="0201 8.06K 1%（QS01 EBOM）")
        rup_a = sheet.pin("Device:R", node_x, base - 7.62, 0, "1")
        rup_b = sheet.pin("Device:R", node_x, base - 7.62, 0, "2")
        power("PWR_3V3A", rup_a[0], rup_a[1] - 7.62)
        sheet.wire(rup_a[0], rup_a[1], rup_a[0], rup_a[1] - 7.62)
        sheet.component("Device:R", f"R{29 + index}", "8.06K", node_x, base + 7.62,
                        footprint="", description="0201 8.06K 1%（QS01 EBOM）")
        rdn_a = sheet.pin("Device:R", node_x, base + 7.62, 0, "1")
        rdn_b = sheet.pin("Device:R", node_x, base + 7.62, 0, "2")
        sheet.wire(rup_b[0], rup_b[1], rdn_a[0], rdn_a[1])
        sheet.junction(node_x, base)
        sheet.label(raw, node_x, base)
        sheet.wire(rdn_b[0], rdn_b[1], rdn_b[0], rdn_b[1] + 3.81)
        power("AGND", rdn_b[0], rdn_b[1] + 3.81)
        # series R + filter C
        sheet.component("Device:R", res, "100R", node_x + 11.43, base, rotation=90,
                        footprint="", description="0201 100R 1%")
        rs_a = sheet.pin("Device:R", node_x + 11.43, base, 90, "1")
        rs_b = sheet.pin("Device:R", node_x + 11.43, base, 90, "2")
        sheet.wire(node_x, base, rs_a[0], rs_a[1])
        sheet.wire(rs_b[0], rs_b[1], 259.08, base)
        sheet.component("Device:C", cap, "100pF", node_x + 24.13, base + 3.81,
                        footprint="", description="0201 100pF 50V C0G")
        cp_a = sheet.pin("Device:C", node_x + 24.13, base + 3.81, 0, "1")
        cp_b = sheet.pin("Device:C", node_x + 24.13, base + 3.81, 0, "2")
        sheet.junction(cp_a[0], base)
        sheet.wire(cp_b[0], cp_b[1], cp_b[0], cp_b[1] + 3.81)
        power("AGND", cp_b[0], cp_b[1] + 3.81)
        sheet.hier_label(net, 259.08, base, shape="output", rotation=0)

    # ======================================================== C 电机温度检测
    sheet.block("C  电机温度检测 NTC (NCP15XH103F03RC)", 20.32, 160.02, 203.2, 198.12)
    sheet.text(
        "note:ntc",
        "3.3V → NTC → 节点 → Rref 6.8kΩ → AGND；25℃ 时节点约 1.335V。"
        " 按 QS01 R25 = 6.8K 修改，NTC 位于电机/丝杠内部。",
        55.88,
        162.56,
        1.27,
    )
    sheet.component(f"{P}:NCP15XH103F03RC", "TH1", "NCP15XH103F03RC", 35.56, 172.72,
                    footprint="", description="0402 10kΩ B3380K NTC")
    th_a = sheet.pin(f"{P}:NCP15XH103F03RC", 35.56, 172.72, 0, "1")
    th_b = sheet.pin(f"{P}:NCP15XH103F03RC", 35.56, 172.72, 0, "2")
    power("PWR_3V3", th_a[0], 166.37)
    sheet.wire(th_a[0], th_a[1], th_a[0], 166.37)
    sheet.component("Device:R", "R32", "6.8K", 35.56, 182.88, footprint="", description="0201 6.8K 1%")
    r32_a = sheet.pin("Device:R", 35.56, 182.88, 0, "1")
    r32_b = sheet.pin("Device:R", 35.56, 182.88, 0, "2")
    sheet.wire(th_b[0], th_b[1], r32_a[0], r32_a[1])
    sheet.junction(th_b[0], 177.8)
    sheet.wire(th_b[0], 177.8, 63.5, 177.8)
    sheet.hier_label("AD_NTC", 63.5, 177.8, shape="output", rotation=0)
    sheet.component("Device:C", "C27", "100nF", 50.8, 181.61, footprint="", description="0201 100nF 16V")
    c27_a = sheet.pin("Device:C", 50.8, 181.61, 0, "1")
    c27_b = sheet.pin("Device:C", 50.8, 181.61, 0, "2")
    sheet.junction(c27_a[0], 177.8)
    sheet.wire(c27_b[0], c27_b[1], c27_b[0], 187.96)
    sheet.wire(r32_b[0], r32_b[1], r32_b[0], 187.96)
    sheet.wire(r32_b[0], 187.96, c27_b[0], 187.96)
    power("AGND", r32_b[0], 187.96)
    sheet.junction(r32_b[0], 187.96)
    sheet.text(
        "note:ntc2",
        "过温降额 85℃ / 硬停机 110℃；固件须用查表或二阶拟合，禁止单系数线性标定",
        22.86,
        193.04,
        1.27,
    )

    sheet.write()
    print(f"wrote {sheet.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
