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
  category_overrides.csv          无有效立创页面器件的分类补充
```

## 分类原则

- 一级目录使用立创分类的第一段，例如 `Capacitors`、`Resistors`。
- 二级目录保留立创分类的细分名称，例如 `Ceramic Capacitors`。
- 每个一级分类包含一个符号库、一个封装库和一个 3D 模型目录。
- `LCSC` 是唯一主键，同一物料不会因位号或项目不同而重复建库。

## 当前状态

- 合并后唯一料号：`105`
- 已完成符号和封装转换：`99`
- 待转换：`6`
- 待转换器件为国内嘉立创 EDA 也未提供 CAD 模型的特殊料号。
- EasyEDA 访问使用国内 `lceda.cn` 接口，避免国际站限流。
- 电阻、电容、磁珠、NTC、LED、二极管和 BAV99 等通用器件可由
  `convert_standard_parts.py` 从 KiCad 10 标准库重复转换。

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

每次转换完成后重新生成索引：

```powershell
C:\Users\15489\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe `
  .\Library\Private\LCSC_Classified\scripts\build_library_index.py `
  .\Library\Private\LCSC_Classified\data\all_parts.csv `
  --library-root .\Library\Private\LCSC_Classified\libraries `
  --output-csv .\Library\Private\LCSC_Classified\data\library_index.csv `
  --output-report .\Library\Private\LCSC_Classified\data\library_index_report.json
```
