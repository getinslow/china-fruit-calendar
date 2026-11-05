# 中国水果产地与物候资料库

按产地查水果，按月份查物候，并保留每条信息的来源、年份和适用范围。数据整理自「果时志」项目，供数据研究、日历、图鉴和其他应用使用。

**2026-11-05 快照：767 条档案，其中 653 条有物候月份，114 条仅有产地资料；另有 637 条品种与风味资料。**

这里的记录单位是“产地与物候证据”，同一水果、同一产地可能有不同品种、阶段、年份或资料口径。不要按名称直接去重或合并月份。数据尚未穷尽全国水果和产区。

## 直接取数据

| 文件 | 内容 |
| --- | --- |
| [data/records-full.json](data/records-full.json) | 完整的 767 条档案与来源，保留嵌套证据 |
| [exports/fruit-seasons.csv](exports/fruit-seasons.csv) | 653 条有月份记录，适合表格读取 |
| [exports/records.csv](exports/records.csv) | 完整档案的主要字段；完整证据请读 JSON |
| [data/origin-profiles.json](data/origin-profiles.json) | 以记录 ID 为键的品种、风味及其来源 |
| [data/search-aliases.json](data/search-aliases.json) | 别名、同义词、品种身份和歧义说明 |
| [data/sources.json](data/sources.json) | 自动生成的来源 URL 与原字段位置索引 |
| [manifest.json](manifest.json) | 文件大小、SHA-256 和自动统计 |

UTF-8 JSON；CSV 使用 UTF-8 BOM，月份以 `|` 分隔。来源索引只索引已存 URL，不表示链接当前可访问，也不表示原站认可本项目。

## 快速开始

需要 Python 3.10+，无需安装依赖、账户、密钥或应用开发工具。

```sh
python scripts/dataset.py validate
python -m unittest discover -s tests -v
python scripts/dataset.py query --fruit 苹果 --month 11 --year 2026
```

编辑数据后重新生成来源索引、CSV 与清单：

```sh
python scripts/dataset.py build
python scripts/dataset.py validate
```

`validate` 只读；`build` 会更新派生文件。查询按水果原名或标题做文字匹配，不执行完整别名扩展。按月查询必须指定年份，避免把其他年度观察混入。无 `year` 的记录也会进入指定年份的查询结果，但应继续阅读其 `harvestWindow`、备注和来源；缺少年份不等于已经验证为常年采季。

## 先读这几条

- `months: []` 表示缺乏可靠月份，不能解读为全年供应。
- `year` 有值的记录保留年度适用限制；单年观察不能外推到每年。
- `opening-only` 只记录起采，不代表完整采季或最佳赏味期。
- `采收`、`食用`、`赏花`、`赏果` 与仅 `产地` 的档案分开；上市、冷藏供应、品牌知名度和图片都不能自动证明采收月份。
- 跨年与分季按原始月份集合读取，中间空档不补齐。
- 原始水果名称和行政区标签尚未统一。例如有月份记录含 63 个原始水果标签，应用曾将部分名称合并为 61 类；58 个原始 `province` 标签也不等于 58 个省级行政区。

详见 [字段说明](docs/DATA.md)、[来源与快照说明](docs/SOURCES.md)、[贡献指南](CONTRIBUTING.md) 和 [第三方内容说明](THIRD_PARTY_NOTICES.md)。

## 收录边界

以原果及其物候、食用和观赏信息为范围，不收录坚果或二次加工成品。保留自然后熟、清洗分装和普通冷藏等处理的语境，不能按备注里出现“干”“糖”等单字排除鲜果。具体规则见 [product-scope.json](data/product-scope.json) 和 [scope-exclusions.json](data/scope-exclusions.json)。

本仓库不包含照片、抓取页面全文、网页应用、小程序、登录提醒后端或个人上线材料。保留的少量证据摘录见第三方内容说明。

## 许可证

可授权的数据编排、原创摘要与文档采用 **[CC BY 4.0](LICENSE)**，允许署名条件下分享、修改与商业使用。脚本、测试与工作流采用 **[MIT](LICENSES/MIT.txt)**。第三方摘录及其他独立权利不由本项目重新授权，具体范围与署名方式见 [LICENSING.md](LICENSING.md)。
