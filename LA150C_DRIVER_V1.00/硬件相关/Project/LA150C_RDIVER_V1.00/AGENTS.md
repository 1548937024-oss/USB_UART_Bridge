# AGENTS.md - LA150C_RDIVER_V1.00

本文件是本 KiCad 工程（`硬件相关/Project/LA150C_RDIVER_V1.00`）的增量规则。
通用画图规范见上级 `AGENTS.md` 与 `docs/KiCad_Schematic_PCB_Design_Spec.md`；
本项目在外置驱动器 MicroDriver V2.10 的绘制经验基础上移植了同一套脚本化流程。

## 工程结构

| 路径 | 说明 |
| --- | --- |
| `scripts/kicad_lib.py` | KiCad 10 原理图生成库（s 表达式读写、坐标栅格、几何审计） |
| `scripts/private_parts.py` | 通用器件 → 分类库料号映射与待确认件清单 |
| `scripts/assemble_library.py` | 组装工程符号库（标准库 + 分类库 + 电源符号） |
| `scripts/build_custom_symbols.py` | 按 datasheet 自建符号（MCU / 功率级 / 编码器 / CAN / DC-DC / 接插件） |
| `scripts/build_project.py` | 写 `.kicad_pro`、`sym-lib-table`、`fp-lib-table` |
| `scripts/build_*_page.py` | 6 张图纸的生成器 |
| `scripts/build_all.py` | 全量重建 |
| `scripts/verify_sheets.py` | 器件越界/重叠、走线穿体的几何审计 |
| `scripts/check_pdf_text.py` | 导出 PDF 的页面与文字越界检查 |
| `scripts/validate.ps1` | 一键：升级 → ERC → 几何审计 → 导出 → PDF 检查 |
| `library/LA150C_RDIVER_V1.00.kicad_sym` | 工程自包含符号库（生成物） |
| `docs/LA150C_绘制规则.md` | 本工程绘制规则 |
| `docs/LA150C_设计说明与待确认项.md` | 电路取值依据与 10 项待确认 |
| `_legacy_altium/` | 重绘前的 Altium 导入版图纸，只作参照，不参与生成与检查 |

## 强制规则

1. **所有图纸由脚本生成。** 禁止手工改 `.kicad_sch` 后当作最终源文件；
   任何修正都要回写到 `scripts/`，再整体重建。
2. **生成后必须 `kicad-cli sch upgrade --force`**，不允许保留旧版本文件头。
3. **交付前必须跑 `scripts/validate.ps1`**，并且满足：
   ERC 0 错误 0 警告、几何审计无问题（含图框越界、器件重叠、走线穿体、
   落进标题栏区域、属性文字重叠）、PDF 文字不越出图框。
4. **一条网络只放一个 `PWR_FLAG`。** 外部连接器输入和经过无源器件之后的
   电源/地网络要补旗标（`VBUS`、`PWR_3V3A` 就是这种情况）。
5. **`#PWRxx` / `#FLGxx` 参考号必须唯一。** 同一页只允许一套递增编号。
6. **跨页信号只走层次端口**；电源与地走工程电源符号，不用普通网络标签替代。
7. **一切对象落在 1.27 mm 栅格上**；走线只允许水平/垂直。
8. **走线不得穿过器件本体**，器件本体不得互相压叠（由 `verify_sheets.py` 把关）。
9. **未使用引脚必须显式 no-connect。**
10. **文档与 datasheet 冲突时以 datasheet 为准，并在图纸上留注记**，
    同时登记到 `docs/LA150C_设计说明与待确认项.md`。
11. **右下标题栏区域 `x ≥ 108 mm && y ≥ 165 mm` 保持空白**，
    该区域属于 `AD_Style_A4.kicad_wks` 自带的修订表与工程标题栏。
12. **同类阻容排列间距不小于 7.62 mm**，避免 Reference / Value 文字相贴；
    测试点只显示位号，Value 隐藏。

## 文字摆放约定（2026-10-04 更新，优先于仓库通用规则）

- **电源符号的 Value 必须显示**，统一放在符号本体右侧、贴着引脚高度，
  不得压在符号图形上；`PWR_FLAG` 不是电源轨名，其 Value 仍隐藏。
  （此项覆盖通用规则里的“电源符号 Value 隐藏”。）
- **元器件的 Reference 与 Value 放在器件上方**，两行水平排列、左对齐：
  Reference 在上、Value 在下，均以器件本体加引脚的外包框为基准。
- **测试点（TPx）只显示位号**，Value（TP0.8）隐藏。
- 图纸模板 `AD_Style_A4.kicad_wks` 已改为精简版：保留双线图框与
  1-6 / A-D 分区标记，去掉四角折页标记，标题栏由 180 × 39 mm 缩小为
  90 × 20 mm（约原面积的四分之一），只保留 Title / Rev / Date / Sheet / Size。
  完整版备份为 `AD_Style_A4_full.kicad_wks`，由 `scripts/build_sheet_template.py` 生成。

## 符号库来源

- 通用阻容与标准器件：KiCad 10 标准库（`Device` / `Connector` / `Transistor_FET`）；
- 已有分类料号：`O-硬件设计/Library/Private/LCSC_Classified/libraries`；
- datasheet 自建：`GD32F503REL7`（BGA64）、`MP6543HGL-Z`、`TCAN3413DDFR`、
  `SCT2230MLUAR`、`SWD-1X3-1.0`、`SOLDER_HOLES_4P_0.5MM`；
- QS01/QS03 对齐料号：`MT6701QT-STD`、`SMF16CA`、`DE5VS06BA`、
  `CSTNE8M00G52A000R0`。

最终图纸只引用工程内 `library/LA150C_RDIVER_V1.00.kicad_sym` 与 KiCad 标准库，
不把安装路径或用户私有路径写进原理图数据。

## 安全与审核边界

- 不自动签署 EMC、安规、热设计或高速信号完整性结论。
- 不在缺少 datasheet、机械尺寸与制造规则的情况下宣称可生产。
- QS03 框图已取消反接 P-MOS；母线 TVS 已选 SMF16CA；MCU 时钟使用外置
  驱动器同款 `CSTNE8M00G52A000R0`。
- 板空间受限，本版取消 CAN CMC 和 60.2Ω/4.7nF 分裂终端，终端由系统/
  线缆端实现；DCDC 输出改为单颗 10µF/10V X7R 0603，8.06k 端接仍属
  待确认件。
- TIMER7 通道与 CAN FD 位时序需固件确认；未关闭前不得进入 PCB 阶段。

## 当前状态

- G3 原理图：ERC 0 错误 0 警告；网表、BOM、PDF 已导出；
  几何审计与 PDF 文字检查通过。
- QS01/QS03 对齐已完成：MCU 改为 BGA64、外部驱动器同款 8MHz 谐振器、
  MT6701QT-STD 校正、CAN FD 仅保留 TCAN3413 + DE5VS06BA、DCDC 前端改为
  SMF16CA + 10µF、nFAULT 改为 1k + 100nF，NTC 为 6.8k 下地。
- MCU 分配已按 `软件相关/QS01-集成驱动器电机控制芯片GD32F503REL7资源配置表V1.xlsx`
  V1.12 对齐：`SPI2_CSN=PA15/A7`、`SPI2_SCK=PB3/A5`、`SPI2_MISO=PC11/B6`、
  `CANFD_RX=PB12/G8`、`CANFD_TX=PB13/G6`；MP6543 `ENA/ENB/ENC` 改为
  10K 上拉 3.3V，不由 MCU 控制；`BOOT0` / `PB2-BOOT1` 均 10K 下拉。
- 对外接口已改为：J1 `1=SWDIO / 2=GND / 3=SWCLK`，3 针 1.0mm；
  J2 为 4 个 Ø0.5mm 焊接孔，Ø0.8mm 焊盘，2.54mm 间距，封装
  `Solder_Holes_4P_0.5mm`。
- 待办：关闭 `docs/LA150C_设计说明与待确认项.md` 中的 TIMER7 通道、
  CAN FD 位时序和 8.06k 端接料号。
