# LCSC 分类私有库

本目录用于把多个嘉立创 BOM 合并为统一的 LCSC 私有库。

## 数据来源

- `../../X200T_ECU_B1_V1.0_20240809(嘉立创).xlsx`
- `../../建库用/BOM_PASTER_8984112A_Y182.xls`
- `../../建库用/BOM_PASTER_8984112A_Y185.xls`
- `../../建库用/BOM_PASTER_8984112A_Y189.xls`
- `../../建库用/BOM_PASTER_8984112A_Y193.xls`
- `../../建库用/BOM_PASTER_8984112A_Y43.xls`
- `../../建库用/BOM_Z300BL_IC-TW39_V1.10.xlsx`
- `manual_imports/LocalParts/parts_review.csv`（非立创在售或手工核准器件）
- `metadata_overrides.csv`（规格书版本、本地归档和人工确认字段）
- `datasheets/`（规格书离线归档）

## 目录结构

```text
LCSC_Classified/
  data/
    all_parts.csv                 合并去重后的器件主表
    library_index.csv             LCSC 到分类库的映射
    category_index.json           分类统计
    categories/                   按立创一级/二级分类保存的 CSV
  libraries/
    Capacitors/
      Capacitors.kicad_sym
      Capacitors.pretty/
      Capacitors.3dshapes/
    Resistors/
    Connectors/
    ...
  scripts/
    parse_legacy_boms.py          读取三个旧式 .xls BOM
    build_classified_library.py   合并并按分类建立库
    build_library_index.py        更新 LCSC 到库文件映射
    convert_pending_parts.py      断点转换剩余器件
    convert_standard_parts.py     从 KiCad 10 标准库补齐通用器件
    library_metadata.py           元数据字段和符号属性同步
    sync_library_metadata.py      用主表回写符号规格书/厂商/MPN
    validate_library_metadata.py  校验规格书和符号元数据
    build_datasheet_manifest.py   生成并校验本地规格书清单
    normalize_3d_model_paths.py   归一化并清理封装 3D 模型路径
    build_3d_manifest.py          校验本地 3D 模型关联
  category_overrides.csv          无有效立创页面器件的分类补充
  metadata_overrides.csv          规格书版本、归档路径和人工核准字段
  excluded_parts.csv              不进入分类库的旧 BOM 占位项
  manual_imports/                 非立创在售件和手工导入件
  datasheets/                     规格书离线归档
```

## 分类原则

- 一级目录使用立创分类的第一段，例如 `Capacitors`、`Resistors`。
- 二级目录保留立创分类的细分名称，例如 `Ceramic Capacitors`。
- 每个一级分类包含一个符号库、一个封装库和一个 3D 模型目录。
- `LCSC` 是唯一主键，同一物料不会因位号或项目不同而重复建库。

## 符号显示值规则

- 电阻、电容、电感符号的 `Value` 必须使用主表 `Value`，显示实际阻值、
  容值或感值，例如 `15kΩ`、`100nF`、`22uH`。
- MPN 只保留在独立 `MPN` 属性中，不再占用 `Value`。
- `sync_library_metadata.py` 会按 LCSC 主键把主表 `Value` 回写到符号，
  `convert_standard_parts.py` 只负责补齐器件几何和封装。
- `validate_library_metadata.py` 会校验电阻、电容、电感的 `Value` 与主表一致。

## 当前状态

- 合并后唯一料号：`101`
- 已完成符号和封装转换：`100`
- 待转换：`1`
- 已关联并完成本地归档的 PDF 规格书：`101`
- 旧 BOM 占位或未确认料号已进入 `excluded_parts.csv`，不再进入主索引。
- `C124020 / TJA1051TK/3,118` 已从有效库排除；CAN FD 替代料
  `C30111221 / TCAN3413DDFR` 已入库并完成本地规格书归档。
- ESD 占位项已替换为 `C54582078 / SLESD11LE5.0C`，封装为
  `DFN0603-2L`。
- EasyEDA 访问使用国内 `lceda.cn` 接口，避免国际站限流。
- 电阻、电容、磁珠、NTC、LED、二极管和 BAV99 等通用器件可由
  `convert_standard_parts.py` 从 KiCad 10 标准库重复转换。
- `GD32F503REL7` 国内立创无在售记录，使用内部主键
  `MANUAL-GD32F503REL7`，按原厂 datasheet 的 BGA64 球号表建库。

## 规格书规则

- `Datasheet` 优先保存官方或 LCSC PDF 地址，不保存商城产品页。
- `DatasheetRev`、`DatasheetDate` 记录规格书版本和日期。
- `LocalDatasheet` 保存仓库内 PDF 相对路径，路径基准为 `data/`。
- 没有可靠规格书的旧料号必须保留 `CLASSIFIED_PARTIAL`。
- 已确认器件的 `Datasheet` 或 `LocalDatasheet` 必须指向 PDF。
- 本地归档文件必须通过 `%PDF` 文件头校验，位置为
  `datasheets/<LCSC>/<MPN>.pdf` 或带版本号的文件名。
- 本地归档清单输出到 `data/datasheet_local_manifest.csv`，校验摘要输出到
  `data/datasheet_local_report.json`。

## Excel 分类索引

`exports/` 下提供两个多 Sheet 工作簿：

- `LCSC_Classified_all_parts_by_category.xlsx`
- `LCSC_Classified_library_index_by_category.xlsx`

每个工作簿包含 `总览` Sheet 和按一级元器件类别拆分的分类 Sheet。分类 Sheet
保留原始字段、筛选按钮、冻结表头和待确认状态高亮。

## PCB 与 3D 关联

- 符号通过 `Footprint` 属性关联 `<分类>:<封装名>`，封装文件位于对应
  `libraries/<分类>/<分类>.pretty/`。
- 封装通过 `(model ...)` 关联 3D 模型。
- 本地模型统一使用 `${LCSC_LIB_ROOT}`，标准 KiCad 模型继续使用
  `${KICAD10_3DMODEL_DIR}`。
- `register_global_libraries.ps1` 会把 `LCSC_LIB_ROOT` 写入
  `kicad_common.json`，同时注册符号库和封装库。
- 当前已转换器件中，`100 / 100` 有可解析的 3D 关联。
- 优先保留已有本地 `.wrl/.step`；缺失模型从国内 LCEDA 获取并归入对应
  `<分类>.3dshapes`，不再重复下载已存在的本地模型。
- 3D 清单输出到 `data/model_3d_local_manifest.csv`，校验摘要输出到
  `data/model_3d_local_report.json`。

## 继续转换

```powershell
C:\Users\15489\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe `
  .\Library\Private\LCSC_Classified\scripts\convert_pending_parts.py `
  --library-index .\Library\Private\LCSC_Classified\data\library_index.csv `
  --library-root .\Library\Private\LCSC_Classified\libraries `
  --easyeda-package .\.codex-compare\easyeda2kicad_pkg `
  --state-file .\Library\Private\LCSC_Classified\data\conversion_state.json `
  --retry-failed `
  --retry-not-found
```

使用 KiCad 10 标准库补齐具备标准符号和封装的器件：

```powershell
C:\Users\15489\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe `
  .\Library\Private\LCSC_Classified\scripts\convert_standard_parts.py `
  --library-index .\Library\Private\LCSC_Classified\data\library_index.csv `
  --library-root .\Library\Private\LCSC_Classified\libraries `
  --state-file .\Library\Private\LCSC_Classified\data\conversion_state.json
```

重建 GD32F503REL7 的 BGA64 符号和标准封装：

```powershell
C:\Users\15489\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe `
  .\Library\Private\LCSC_Classified\scripts\import_gd32f503rel7_symbol.py `
  --source-library .\Microdriver\03-硬件相关\01-PRO\MicroDriver_V2.10\library\MicroDriver_V2.10.kicad_sym `
  --library-root .\Library\Private\LCSC_Classified\libraries `
  --kicad-root D:\KiCad10.0
```

该符号的球号表来自 `GD32F503xx_Datasheet_Rev0.9RC6.pdf`，封装为
`ucBGA-64_4x4mm_Layout8x8_P0.4mm`。

每次转换完成后重新生成索引：

先重建主表和分类表：

```powershell
C:\Users\15489\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe `
  .\Library\Private\LCSC_Classified\scripts\build_classified_library.py `
  .\Library\Private\ExternalDriver\projects\X200T_ECU_B1_V1.0_20240809\parts_enriched.csv `
  .\Library\Private\LCSC_Classified\legacy_import\parts_enriched.csv `
  .\Library\Private\LCSC_Classified\new_imports\Y193\parts_review.csv `
  .\Library\Private\LCSC_Classified\new_imports\Y43\parts_review.csv `
  .\Library\Private\LCSC_Classified\new_imports\Z300BL\parts_review.csv `
  .\Library\Private\LCSC_Classified\manual_imports\LocalParts\parts_review.csv `
  --overrides .\Library\Private\LCSC_Classified\category_overrides.csv `
  --metadata-overrides .\Library\Private\LCSC_Classified\metadata_overrides.csv `
  --exclude-parts .\Library\Private\LCSC_Classified\excluded_parts.csv `
  --output-dir .\Library\Private\LCSC_Classified
```

把主表元数据同步回符号：

```powershell
C:\Users\15489\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe `
  .\Library\Private\LCSC_Classified\scripts\sync_library_metadata.py `
  .\Library\Private\LCSC_Classified\data\all_parts.csv `
  --library-root .\Library\Private\LCSC_Classified\libraries
```

重新生成索引并执行元数据校验：

```powershell
C:\Users\15489\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe `
  .\Library\Private\LCSC_Classified\scripts\build_library_index.py `
  .\Library\Private\LCSC_Classified\data\all_parts.csv `
  --library-root .\Library\Private\LCSC_Classified\libraries `
  --output-csv .\Library\Private\LCSC_Classified\data\library_index.csv `
  --output-report .\Library\Private\LCSC_Classified\data\library_index_report.json

C:\Users\15489\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe `
  .\Library\Private\LCSC_Classified\scripts\validate_library_metadata.py `
  .\Library\Private\LCSC_Classified\data\all_parts.csv `
  --library-root .\Library\Private\LCSC_Classified\libraries `
  --library-index .\Library\Private\LCSC_Classified\data\library_index.csv `
  --report .\Library\Private\LCSC_Classified\data\metadata_validation_report.json
```
