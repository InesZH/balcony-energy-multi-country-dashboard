# 德国阳台储能市场数据监测看板

Germany Balcony Energy Storage Market Dashboard

这是一个基于真实 Excel 数据构建的单页面 Streamlit 交互看板，覆盖品牌表现、容量段结构、市场份额变化和核心竞品价格追踪。KPI、图表、环形图和价格表均由同一源文件实时计算。

## 启动

在项目根目录 PowerShell 中运行：

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r dashboard\requirements.txt
python -m streamlit run dashboard\app.py
```

浏览器通常会自动打开 `http://localhost:8501`。如果 PowerShell 阻止激活虚拟环境，可以直接运行：

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard\app.py
```

## 项目结构

```text
dashboard/
  app.py
  data_processing.py
  charts.py
  config.py
  data/
    德国亚马逊.xlsx
  tests/
    test_data_processing.py
    test_charts.py
    test_app.py
  .streamlit/
    config.toml
  requirements.txt
  README.md
```

## 数据更新

1. 用新的 Excel 覆盖 `dashboard/data/德国亚马逊.xlsx`。文件名可保留不变。
2. 保持工作表名称、表头位置和月度字段格式一致：`YYYY-MM` 或 `YYYY-MM(€)`。
3. 新增 2026 年月份时无需改代码；新增列会自动进入日期解析和图表计算。
4. 如需新增 2027 年，修改 `config.py` 中的 `REPORT_YEARS`，并在 `app.py` 的年份筛选器中加入对应选项。
5. 更新后刷新浏览器。Streamlit 会根据文件修改时间重新加载并缓存数据。

如需把源文件放在其他位置，可设置环境变量：

```powershell
$env:BALCONY_DATA_PATH = "D:\data\德国亚马逊.xlsx"
python -m streamlit run dashboard\app.py
```

## 当前数据覆盖

- 数据时间：2025-01 至 2026-10
- ASIN 明细：89 个
- 源品牌：27 个
- 重点品牌：Anker、ECOFLOW、Hoymiles、Jackery、MARSTEK、Mentech、Powerness、Solakon、SUNNIVA、TSUN、Zendure、ZINNZGREEN
- 其他品牌：源数据中的真实聚合，看板显示为 `Other brands`
- 核心价格产品：指定 11 个 ASIN
- 2026 年 11–12 月尚未提供，因此 2026 年 KPI 为年初至今口径

## 源表与看板字段映射

| 源工作表 | 原始字段 | 看板字段 / 用途 |
|---|---|---|
| 产品历史月销量 | ASIN | ASIN，产品唯一键；仅在内部关联，不在价格模块界面展示 |
| 产品历史月销量 | brand | Brand，并按重点品牌映射为 Brand Display |
| 产品历史月销量 | 容量（文本列与数值列） | Capacity Wh |
| 产品历史月销量 | 容量段 | 用于校验；看板按业务边界重新计算 Capacity Segment |
| 产品历史月销量 | 商品标题 | Product Name |
| 产品历史月销量 | 2025-01 … 2026-10 | Date、Year、Month Number、Units |
| 历史月销售额 | 2025-01(€) … 2026-10(€) | Revenue，按 ASIN × 月份合并 |
| 历史月价格 | 2025-01(€) … 2026-10(€) | Price，按 ASIN × 月份合并 |
| 按品牌，25/26月销量 | 求和项:YYYY-MM | 品牌销量汇总，用于对账 |
| 按容量段，25/26月销量 | 求和项:YYYY-MM | 容量段销量汇总，用于对账 |
| 产品信息 | 商品标题、价格(€) 等 | 当前快照；不替代历史价格 |

## 主口径与对账

看板以 `产品历史月销量`、`历史月销售额`、`历史月价格` 的 ASIN × 月份明细为主口径。

原因如下：

1. ASIN 明细的月度销量与容量段汇总表逐月完全一致。
2. ASIN 明细同时具有销量、销额、容量和价格，能够保证各模块能使用同一产品集。
3. 品牌汇总表与 ASIN 明细存在少量月度差异，因此仅用于数据质量对账，不与 ASIN 明细混加。
4. `产品信息` 是当前快照，不适合代替历史时间序列。

当前检查结果：

- ASIN 明细与容量段汇总的最大月度差异：0 units。
- 品牌汇总表与 ASIN 明细存在 10 条月度差异记录，主要在个别品牌。详细行显示在看板底部数据质量区。
- 源表中有 4 个 ASIN 的容量段标签与业务边界不一致，容量段模块已统一重算。
- 指定 11 个价格产品均能在源价格表中找到，但部分产品在上市前或未采集月份没有价格。

## 清洗规则

### 品牌标准化

品牌名称去空格并统一大小写。常见别名映射到固定名称，例如 `ANKER` → `Anker`、`ECOFLOW`/`EcoFlow` → `ECOFLOW`、`MARSTEK`/`Marstek` → `MARSTEK`。

品牌图使用与容量段图一致的柔和蓝绿、沙金配色，同一品牌在各图表中保持固定颜色。其余真实品牌聚合为
`Other brands`，使用灰蓝色。为减少首图的视觉噪声，`TSUN`、`Mentech`、`Jackery` 默认也并入该图的
`Other brands` 分段；KPI 和各品牌筛选仍使用完整明细，合并只影响首图展示，不改变总量。

### 容量标准化

- 纯数字按 Wh 处理。
- `Wh` 后缀按 Wh 处理。
- `kWh` 后缀乘以 1000，转换为 Wh。
- 统一存储数值型 Wh，并使用以下互斥区间：

| 容量段 | 区间 |
|---|---|
| `<2kWh` | `capacity < 2000` |
| `2-3kWh` | `2000 <= capacity < 3000` |
| `3-4kWh` | `3000 <= capacity < 4000` |
| `4-5kWh` | `4000 <= capacity <= 5000` |
| `>5kWh` | `capacity > 5000` |

### 日期与月份

从 `YYYY-MM` 和 `YYYY-MM(€)` 字段解析真实月份日期，提取 Year、Month Number 和 Month Label。图表按日期排序，不按月份字符串字母排序。当前年份即使没有 11–12 月记录，品牌与容量段图仍保留 12 个月横轴，以明确显示缺失位置。

### 缺失与异常值

- 销量、销额、价格缺失保持空值，不填充为 0。
- 求和时只汇总有效值；如果某一维度在某月没有任何有效值，结果保持空值。
- 真实 0 units、0 revenue 保留。
- 价格 `<= €0` 在价格分析中视为不可用价格，不作为真实售价；原始 0€ 异常数量保留在数据质量检查中。
- 价格折线使用 `connectgaps=False`，缺失月份显示断点，不跨月插值。

### 重复记录

检查 ASIN × 月份重复记录。若发现重复，程序会阻止计算并给出明确错误，不直接删除记录或让销量无声翻倍。

## 指标定义

- Total Units：当前筛选下所有有效 Units 之和。
- Total Revenue：当前筛选下所有有效 Revenue 之和，单位为欧元。
- Units Share：当前维度 Units / 当前筛选市场 Units × 100%。
- Revenue Share：当前维度 Revenue / 当前筛选市场 Revenue × 100%。
- Share Change：2026 Share − 2025 Share，单位为百分点 `pp`。
- Average Price：筛选期间各实际月度售价的算术平均。
- Minimum / Maximum Price：筛选期间真实月度售价的最小值和最大值。
- Latest Price：筛选期间最新可用月份的实际价格。
- Previous Month Price：Latest Month 前一个自然月的实际价格；该月缺失时留空。
- Price Change：`(Latest Price - Previous Month Price) / Previous Month Price × 100%`。
- Price per kWh：`Latest Price / (Capacity Wh / 1000)`。

## 交互说明

- 年份、品牌、容量段和产品系列筛选均会重新计算 KPI 和图表。
- 品牌与容量段图默认每月仅展示一根堆叠大柱，柱内按品牌或容量段分色；品牌图另支持排名趋势模式。
- 品牌图选择全部品牌时，销额折线只显示一条 Total Revenue 合计线；减少任一品牌后，按品牌显示各自销额折线。
- 价格模块用“品牌 · 系列 · 容量 Wh”识别和展示产品，不展示 ASIN。
- 图表图例可切换系列，模式栏支持缩放、平移、重置和下载 PNG。
- 市场份额支持 Brand / Capacity Segment 与 Units / Revenue 切换。
- 热力图支持 2025/2026 与 Units/Revenue 切换。
- 价格表可下载为 UTF-8 BOM CSV，便于 Excel 直接打开。

## 验证

运行自动化测试：

```powershell
cd dashboard
..\.venv\Scripts\python.exe -m pytest -q tests
```

当前测试覆盖：

- 源数据覆盖与关键字段
- 容量边界与容量段互斥
- 品牌、容量段份额之和为 100%
- ASIN 明细与容量段汇总对账
- 年份和品牌筛选
- 缺失值与价格异常处理
- 价格变化率计算
- 七张 Plotly 交互图
- Streamlit 完整页面和筛选器交互

## 数据限制

- 2026 年只有 1–10 月，不能把 2026 总量直接解释为完整年度总量。
- 品牌汇总表与 ASIN 明细有少量对账差异，看板没有通过补齐、分摊或估算消除差异。
- 部分 ASIN 无完整 22 个月价格，历史折线会显示真实断点。
- 价格 0€ 的具体记录数量会随源数据更新而变化，最新结果以看板底部数据质量区为准。
