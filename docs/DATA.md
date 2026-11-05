# 数据与字段

## 记录单位与时间

`data/records-full.json` 是完整发布快照。稳定 `id` 连接其他文件；它是资料记录的标识，不是果园、品牌或行政区的统一编码。

`months` 是原文支持的月份集合，数组顺序保留原样。`[11,12,1]` 可以表示跨年窗口，`[5,6,10,11]` 中的两段不能填成 5–11 月。月份不精确到日；`sourcePeriod` 和备注可能提供旬、品种或海拔等限制。`year` 限定年度，出版日期 `sourceDate` 与观察日期 `observedDate` 不同。跨年记录的年度归属应结合备注，不凭数字数组自动推算相邻年度日期。

## 完整记录字段

“可选”字段可能完全不存在；不存在不自动等于否定、零或空字符串。

| 字段 | 类型 | 必需 | 含义 |
| --- | --- | --- | --- |
| `id` | string | 是 | 稳定且全库唯一的记录 ID |
| `fruit` | string | 是 | 原始水果分类标签，未完全归一化 |
| `title` | string | 否 | 更具体的地方产品或品种标题 |
| `province` | string | 是 | 原始省级地区标签，可能使用简称或全称 |
| `place` | string | 是 | 具体地点文字；无统一行政区编码保证 |
| `kind` | string | 是 | `采收`、`食用`、`赏花`、`赏果`、`产地` |
| `months` | integer[] | 是 | 1–12 的不重复月份；空数组为未知 |
| `note` | string | 是 | 编辑说明、证据摘要与适用限制 |
| `sourceTitle` | string | 是 | 主来源标题或编辑形成的来源标注 |
| `url` | string | 是 | 主来源 HTTP(S) 地址 |
| `year` | integer | 否 | 记录限定的年度；不可自动每年复用 |
| `harvestWindow` | string | 否 | 下表的时间证据口径 |
| `sourcePeriod` | string | 否 | 来源中的果期文字，保留原精度 |
| `startDate`、`endDate` | string | 否 | YYYY-MM-DD，来源明确支持的日期 |
| `observedDate` | string | 否 | YYYY-MM-DD，现场观察日期 |
| `sourceDate` | string | 否 | 出版日期，YYYY、YYYY-MM 或 YYYY-MM-DD；不虚构日 |
| `checkedAt` | string | 否 | YYYY-MM-DD，已有研究记录的检查日期；不代表本仓库发布时重新读过原文 |
| `forecastMonths` | integer[] | 否 | 来源中的预测月份，不能视为已发生采收 |
| `locationPrecision` | string | 否 | 地点匹配精度与限制 |
| `applicability` | string | 否 | 品种等适用边界 |
| `evidenceSummary` | string | 否 | 补充证据说明 |
| `sourceCategory`、`sourceRecord` | string | 否 | 原始登记类别与记录号 |
| `supportingUrl`、`supportingSourceTitle` | string | 否 | 补充来源地址与标题，标题可能缺失 |
| `additionalSources` | object[] | 否 | 多条补充来源，主要包含 `sourceTitle`、`url` |
| `originSource` | object | 否 | 补入月份前的原产地来源；不是当前采期的直接证据 |
| `knownOrigin` | object | 否 | “知名产地”的编辑性依据，不是品质认证 |
| `knownOriginHistory` | object[] | 否 | 以往知名产地依据，保留真实年份 |
| `brandEvidence` | object | 否 | 品牌榜单证据，含品牌名、年份、名次、来源地区、URL 等 |
| `brandEvidenceHistory` | object[] | 否 | 历史品牌证据 |
| `brandSearchNames` | string[] | 否 | 品牌搜索用名；不自动认定为同品种 |

`knownOrigin` 常见子字段：`label`、`reason`、`sourceTitle`、`url`，以及可选的 `sourceYear`、`sourceBrand`、`scopeRelation`。品牌榜单年份不等于果期观察年份。`originSource` 可含原来的 `url`、`sourceTitle`、`sourceDate`、`note`；嵌套原始字段应保留。

| `harvestWindow` | 解释 |
| --- | --- |
| `annual-observation` | 限定年份的观察；必须有 `year` |
| `opening-only` | 只有起采信息，不代表完整持续时间；也可能有年度限制 |
| `seasonal-reference` | 资料提供的采季参考；若仍有 `year`，优先保留年度限制 |
| 未填写 | 历史记录未作此分类，应读年份、备注与来源，不能自动归为常年 |

## 其他文件

`origin-profiles.json`：对象键是记录 ID；`fields` 映射中文字段名到展示文字。来源有两种形式：`source` 为单 URL，或 `sources` 为对象数组（常见 `title`、`url`、`evidence`）。品种、果园、登记产品和产区描述不能不加区别地推广到所有记录；保留原有文字边界。

`search-aliases.json`：`groups` 中包含 `canonical`、`aliases`、`targetType`、`fruitNames`、`identityTerms`、`recordIds`、`sourceIds`、`ambiguity` 等。`targetType` 可区分水果、品种和歧义名称；别名相似不意味着植物身份相同。`sources` 的键可由 `sourceIds` 连接。`recordBindings` 保留对具体记录的受限匹配说明。这里只发布原规则与证据，不实现应用原来的搜索算法。

`season-revisions.json`：保留一条已反映在完整快照中的修订及旧版本语境；`previousObservation` 是历史，不能作为新增的现行记录。`researchFile` 是原项目相对路径，部分研究文件未包含于此仓库；这些路径不是下载地址，也不是运行依赖。

`product-scope.json`、`scope-exclusions.json`：收录规则和当时的范围复核记录。历史基线数字不等于当前快照的统计值。

## 导出、来源索引与清单

CSV 是主要字段的扁平投影，不包含全部嵌套来源；空单元格表示该字段不存在或为空。`months` 用 `|` 连接。为防止表格软件执行公式，新增文本以 `= + - @` 等字符开头时，导出会前置单引号；JSON 保留原文。

`data/sources.json` 按完整 URL 精确去重，保留 fragment 与查询参数。`references` 的 `file` 和 `pointer` 指向输入文件和路径，部分条目另含 `recordId`。URL 的存在不代表网络、证据或许可检查已经通过。

`manifest.json` 对六个输入 JSON、来源索引和两个 CSV 记录 SHA-256。`validate` 会重算并逐字节比较导出与清单，检测过期导出和未同步的输入更改。更新后请先审阅 diff，再运行 `build` 更新清单；清单不是数字签名，也不能替代来源核验。
