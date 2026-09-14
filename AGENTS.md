# AGENTS.md

本文件是本仓库中 Codex 执行 PCB/KiCad 相关任务时必须遵守的项目级规范。

## 项目目标

在当前仓库内建立一套可复现、可审核、可版本控制的 KiCad PCB 开发流程。
流程以 Codex、`kicad-cli`、`pcbnew` 和脚本化检查为核心，演示项目为隔离型
USB 转 UART 小板。

## 当前演示项目

项目目录：

`Codex_KiCad_USB_UART_Demo/`

核心文件：

- `hardware/USB_UART_Bridge/USB_UART_Bridge.kicad_sch`
- `hardware/USB_UART_Bridge/Power.kicad_sch`
- `hardware/USB_UART_Bridge/Communicate.kicad_sch`
- `hardware/USB_UART_Bridge/USB_UART_Bridge.kicad_pro`
- `hardware/USB_UART_Bridge/sym-lib-table`
- `hardware/USB_UART_Bridge/fp-lib-table`
- `requirements.yaml`
- `design_intent.yaml`
- `scripts/generate_schematic.py`
- `scripts/validate.ps1`
- `reports/erc.json`
- `generated/USB_UART_Bridge.net`
- `generated/USB_UART_Bridge_BOM.csv`
- `manufacturing/USB_UART_Bridge.pdf`

## 原理图层次结构

- 顶层图纸只放外部接口和对应电气网络。
- USB-C、USB ESD、CC 下拉、UART 接口和 VOUT 选择放在顶层图纸。
- `Power.kicad_sch` 放保险丝、隔离电源、隔离侧 LDO 和相关去耦。
- `Communicate.kicad_sch` 放 USB-UART 桥、数字隔离器和辅助状态电路。
- 跨图纸信号使用层次标签和图纸引脚连接。
- 电源网络必须使用 `power` 库中的电源符号，不得使用普通网络标签。
- 非电源网络使用实际走线连接，按曼哈顿距离建立最小生成树并优先选择较短路径。

## 环境约束

- 优先使用本机 `D:\KiCad10.0` 中的 KiCad 10。
- 如果首选路径不存在，再检测 `C:\Program Files\KiCad\10.0`。
- 自动化检查和导出优先使用 `kicad-cli`。
- 需要操作电路板对象时使用 KiCad 安装目录中的 `pcbnew` Python API。
- 不允许把 KiCad 安装路径、临时目录或用户私有路径硬编码到最终原理图数据中。

## USB 转 UART 设计要求

### 隔离

- USB 数据 D+/D- 不做隔离。
- USB 供电和串口供电必须隔离。
- 隔离等级目标为 `1.5 kVrms`。
- 隔离侧和 USB 侧必须使用独立地：`GND_ISO` 和 `GND_USB`。
- 隔离带内禁止铜皮、走线或过孔跨越。
- 隔离爬电距离不小于 `5 mm`。
- 建议在隔离带下设置板边开槽，以提高隔离可靠性。

### 信号

- 只隔离 `TXD` 和 `RXD`。
- 不保留 `DTR`、`RTS`。
- 支持连续全双工，最高 `5 Mbps`。
- UART 逻辑固定为 `3.3 V`。
- 如果需要 5 V UART 逻辑，必须另加电平转换，不能直接改变隔离侧 I/O 电压。

### 关键器件选择

- USB-UART 桥：`CH343G`，最高 `6 Mbps`。
- 数字隔离器：`ISO7721D`，双通道、最高 `100 Mbps`。
- 隔离电源：`CRE1S0505SC`，5 V 输入、5 V 隔离输出、1 W。
- 隔离侧 LDO：`AP2112K-3.3`。
- USB ESD 保护：`USBLC6-2SC6`。
- USB 接口：USB-C，USB 2.0 16P。
- 隔离输出选择：`JP1` 三针排针。

禁止在 5 Mbps 要求下重新使用 `CP2102N` 作为主桥，因为其 UART 速率不足以
覆盖该要求。

## 输出接口要求

- J2 使用 `1x4`、`2.54 mm` 排针。
- J2 引脚顺序固定为：
  1. `GND_ISO`
  2. `VOUT_ISO`
  3. `TXD`
  4. `RXD`
- `VOUT_ISO` 通过 `JP1` 选择隔离 `3V3_ISO` 或隔离 `5V_ISO`。
- 隔离输出最大负载按 `100 mA` 设计。
- `VOUT_ISO` 只改变参考电源输出，不改变 TXD/RXD 的 3.3 V 逻辑电平。

## 原理图规范

- 原理图必须使用 A4 图纸。
- 器件按信号或电流流向排列。
- 电源网络位于图面上方或左侧。
- GND 网络位于图面下方或右侧。
- 信号主流程优先从左到右，其次从上到下。
- USB 输入放在左侧。
- USB-UART 桥放在中间偏左。
- 隔离器放在中间偏右。
- 隔离输出放在右侧。
- 电源转换链放在图面上方。
- 原理图按功能划分为 USB 输入、桥接、隔离、隔离电源和输出区。
- 网络标签不能直接压在器件引脚端点上。
- 每个网络标签应连接到一段清晰的引脚走线末端。
- 引脚走线默认长度为 `7.62 mm`，可根据图面可读性调整。
- 不同网络的走线不得交叉或重叠。
- 器件原点、全部器件引脚、走线端点、网络标签和 no-connect 必须落在
  KiCad 默认的 `1.27 mm` 栅格上。
- 禁止使用半格或任意小数坐标放置原理图对象。
- 电源标签朝上或左，GND 标签朝下或右。
- 未使用引脚必须显式放置 `no_connect`。
- 电源网络必须满足 ERC 的驱动要求。

## PCB 约束

- PCB 层数：`2` 层。
- 板厚：`1.6 mm`。
- 铜厚：`1 oz`。
- 表面处理：无铅喷锡。
- 优先使用嘉立创、立创商城常用料。
- 最小线宽初始值：`0.20 mm`。
- 最小间距初始值：`0.20 mm`。
- 最小钻孔初始值：`0.30 mm`。
- 隔离侧和 USB 侧必须独立铺铜。
- USB 差分对优先短距离、同层、等长布线，并保持参考平面连续。
- 隔离电源输入、输出和 LDO 去耦必须靠近对应器件。

## 自动化工作流

所有设计变更必须尽可能通过脚本生成，禁止直接手工修改生成物后再作为最终
源文件提交。

标准流程：

1. 修改 `requirements.yaml`。
2. 修改 `design_intent.yaml`。
3. 修改 `scripts/generate_schematic.py`。
4. 生成原理图。
5. 运行 ERC。
6. 导出网表、BOM 和 PDF。
7. 检查不同网络走线交叉数量为 0。
8. 更新版本说明后进入 PCB 阶段。

生成原理图：

```powershell
D:\KiCad10.0\bin\python.exe .\scripts\generate_schematic.py
```

执行验证和导出：

```powershell
pwsh -NoProfile -File .\scripts\validate.ps1
```

## 发布关口

- G0 环境：KiCad CLI 和 `pcbnew` 可用。
- G1 需求：需求可测试且无歧义。
- G2 架构：器件、封装、电源和复位已验证。
- G3 原理图：ERC 无错误、无警告，网表和 BOM 已生成。
- G4 布局：机械配合、隔离带和去耦位置已验证。
- G5 布线：连通性、USB 差分对和电源回流已验证。
- G6 DRC：DRC 和原理图一致性检查通过。
- G7 制造：Gerber、钻孔、坐标和 STEP 完整。
- G8 发布：干净环境可复现，输出可追溯。

## 安全和审核边界

- 不自动签署 EMC、安规、热设计或高速信号完整性结论。
- 不在没有数据手册、机械尺寸和制造规则的情况下宣称设计可生产。
- 不跨越隔离带自动布线。
- 不把 `GND_USB` 和 `GND_ISO` 连接为同一网络。
- 不把 `VOUT_ISO` 的 5 V 选项误解为 5 V UART 逻辑。

## 当前状态

- P0 环境锁定：已完成。
- P1 需求锁定：已完成。
- P2 架构与选型：已完成。
- P3 原理图：已完成，顶层、Power 和 Communicate 均为 A4 图纸，ERC 为 0 错误、0 警告。
- P4 PCB 设置与布局：尚未开始。

每次进入下一阶段前，优先检查本文件与项目中的 `requirements.yaml`、
`design_intent.yaml` 和生成脚本是否仍然一致。
