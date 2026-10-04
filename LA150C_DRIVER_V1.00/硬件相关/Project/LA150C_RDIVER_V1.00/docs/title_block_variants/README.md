# LA150C 标题栏候选格式

以下文件只替换 A4 图框的右下角标题栏，不改原理图内容。

| 候选 | 标题栏尺寸 | 主要字段 | 预览 |
| --- | --- | --- | --- |
| 01_slim_current | 90 x 20 mm | Title / Rev / Date / Sheet / Size | `preview/01_slim_current-1.png` |
| 02_compact_engineering | 110 x 24 mm | Title + subtitle / Rev / Date / Sheet / Size | `preview/02_compact_engineering-1.png` |
| 03_engineering_revision | 150 x 30 mm | Title + subtitle / Rev / Date / Sheet / Size / Doc No. / revision table | `preview/03_engineering_revision-1.png` |
| 04_ad_full | 180 x 39 mm | 完整 AD 工程栏 + 双行修订表 | `preview/04_ad_full-1.png` |
| 05_ad_frame_compact_title | AD 图框 + 110 x 24 mm 紧凑标题栏 | 保留 04 的四角折页与分区，右下角使用 02 布局 | `preview/05_ad_frame_compact_title-1.png` |

预览使用同一份标题栏数据：

- Title: `LA150C RDIVER V1.00`
- Subtitle: `LA150C 集成驱动器原理图`
- Rev: `V1.00`
- Date: `2026-10-04`
- Doc No.: `LA150C-RDIVER-SCH-001`

已选定 `05_ad_frame_compact_title`，并同步为工程默认 `AD_Style_A4.kicad_wks`。
