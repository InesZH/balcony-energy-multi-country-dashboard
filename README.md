# 多国家阳台储能市场数据监测看板

这是一个把 France 与 Germany 两个既有 Streamlit + Plotly 看板整合到同一入口的多国家 Dashboard。页面顶部提供 Country Selector，默认显示 France；切换国家后加载该国原有的完整 KPI、图表、筛选器、价格表和质量检查。

整合采用代码级路由，不使用 iframe。法国和德国各自保留独立的数据文件、模块、统计口径与筛选器，不进行跨国求和或共享 KPI。

德国原看板源码来自其公开 GitHub 仓库：

`https://github.com/ineszh/germany-balcony-energy-dashboard`

本项目的德国数据已更新为用户提供的 `德国亚马逊.xlsx`。

## 启动

建议使用 Python 3.12。

```powershell
cd dashboard
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

浏览器打开终端显示的本地地址，通常为 `http://localhost:8501`。

桌面端、平板和窄屏使用统一的 `900px` 响应式断点：筛选器、KPI 和双栏图表容器会按同一规则纵向排列，避免 France 与 Germany 页面在相同宽度下出现不同布局。

GitHub 上传和 Streamlit Cloud 公网部署步骤见 [DEPLOYMENT.md](DEPLOYMENT.md)。

本项目已在以下版本完成实际运行和测试：

- Streamlit 1.67.0
- Plotly 7.1.0
- pandas 3.1.1
- openpyxl 3.1.5

运行数据与图表测试：

```powershell
$env:PYTHONPATH=(Get-Location)
python -m pytest -q
```

## 项目结构

```text
dashboard/
├─ app.py
├─ france_dashboard.py
├─ data_processing.py
├─ charts.py
├─ config.py
├─ countries/
│  └─ germany/
│     ├─ dashboard.py
│     ├─ data_processing.py
│     ├─ charts.py
│     ├─ config.py
│     ├─ data/德国亚马逊.xlsx
│     └─ tests/
├─ data/
│  ├─ 法国亚马逊.xlsx
│  └─ product_name_overrides.csv
├─ tests/
│  └─ test_dashboard.py
├─ .streamlit/
│  └─ config.toml
├─ requirements.txt
└─ README.md
```

`app.py` 是唯一入口。`france_dashboard.py` 与 `countries/germany/dashboard.py` 分别渲染两个国家，二者使用各自的 `config.py`、`data_processing.py` 和 `charts.py`。

## 月度数据更新

法国默认读取 `data/` 中修改时间最新的 Excel 文件。德国默认读取 `countries/germany/data/德国亚马逊.xlsx`。

如需读取其他位置的法国或德国文件：

```powershell
$env:DASHBOARD_DATA_FILE="D:\market-data\法国亚马逊.xlsx"
$env:BALCONY_DATA_PATH="D:\market-data\德国亚马逊.xlsx"
streamlit run app.py
```

法国必需工作表及固定用途如下：

| 工作表 | 用途 |
|---|---|
| `产品历史月销量` | ASIN 月度销量明细 |
| `历史月销售额` | ASIN 月度销额明细 |
| `FR-FRsolarstoragesystem(84)` | 当前产品主表、容量、标题和品牌 |
| `历史月价格` | ASIN 月度历史价格 |

如果工作表名称改变，需要在 `config.py` 的 `SHEET_CANDIDATES` 中更新候选名称。缺少必需工作表时，应用会停止加载并明确报错，不会生成替代数据。

## 字段映射

| 看板字段 | 原字段/来源 | 处理规则 |
|---|---|---|
| `asin` | `ASIN` | 去空格、转大写；仅用于后台关联，不显示在图表、图例或价格表 |
| `brand` | `brand`、`品牌`、价格表商品标题 | 品牌名称标准化；销量/销额以当前产品主表为优先 |
| `capacity_wh` | `容量` | 转为数值型 Wh |
| `capacity_segment` | 由 `capacity_wh` 重算 | 按统一互斥边界分组 |
| `title` | `商品标题` | 保留原始标题，用于系列名称提取和人工复核 |
| `product_name` | 品牌 + 标题中的系列/型号 + 容量 | 不展示 ASIN；无法确认容量时明确标记 |
| `units` | 月销量表各月份列 | 缺失保持缺失，真实 0 保持 0 |
| `revenue` | 月销额表各月份欧元列 | 缺失保持缺失，真实 0 保持 0 |
| `price` | 历史月价格各月份欧元列 | 空值和 0 均视为缺失，不插值 |
| `month` | 月份列名 | 转为 `YYYY-MM`，按自然时间排序 |

## 清洗与计算口径

品牌统一规则包括：

- `ANKER`、`Anker` → `Anker`
- `Ecoflow`、`EF ECOFLOW` → `EcoFlow`
- `MARSTEK` → `Marstek`
- `ZENDURE SuperCharged` → `Zendure`
- `TSUN`、`Mentech` 不单独展示

容量分组严格互斥：

| 原始容量 | 容量段 |
|---|---|
| `< 2,000Wh` | `<2kWh` |
| `2,000–2,999Wh` | `2–3kWh` |
| `3,000–3,999Wh` | `3–4kWh` |
| `4,000–5,000Wh` | `4–5kWh` |
| `> 5,000Wh` | `>5kWh` |

关键计算：

- Total Units：选中范围内的有效销量求和。
- Total Revenue：选中范围内的有效销售额求和，单位欧元。
- 销量占比：品牌/容量段销量 ÷ 同期市场有效销量。
- 销额占比：品牌/容量段销额 ÷ 同期市场有效销售额。
- 市场份额变化：`2026 Share − 2025 Share`，结果以百分点 `pp` 展示。
- 价格变化率：`(Latest Price − Previous Month Price) / Previous Month Price × 100%`。
- Price per kWh：`Latest Price / (Capacity Wh / 1000)`；容量无法可靠识别时不计算。
- Latest Price：筛选期间最后一个有效价格；同时显示其来源月份。
- Previous Month Price：最新价格月份的紧邻上一自然月。若该月无有效价格，则不计算变化率。

分析范围固定为用户要求的 2025–2026 年。原始明细还包含 2024-11 和 2024-12，但不纳入当前看板的年份选项和汇总。

销量与销额来自 ASIN×月明细，不使用“汇总页 + 明细”重复相加。8 张品牌/容量段汇总页仅用于交叉校验。

## 交互与显示

- 模块一：年份、品牌多选；全部品牌时只用一条“市场总销额”线，部分品牌时按选中品牌拆线。
- 模块二：年份、品牌多选；每月一个堆叠柱，五个容量段共用固定颜色。
- 模块三：2025/2026 双年度环形图、份额变化图和可选热力图；支持品牌/容量段和销量/销额切换。
- 模块四：年份、品牌、容量段和产品选择；历史价格折线在缺失月份断开，价格表不展示 ASIN。
- 所有 Plotly 图表支持悬浮提示、图例显隐、缩放、平移、自动缩放、重置和 PNG 导出。

同一品牌在全部图中使用固定色；同一容量段在堆叠柱、折线、环形图和热力图中保持统一口径。产品颜色由品牌基础色和稳定的 ASIN 哈希派生，刷新或筛选不会随机变化。

## 产品名称校正

产品名称优先从原始标题提取品牌、系列/型号和容量。无法可靠判断容量、或标题属于特殊配置时，使用以下内部文件人工校正：

`data/product_name_overrides.csv`

文件字段为 `ASIN,display_name`。ASIN 只在这个后台文件中用于唯一匹配，不应在界面显示。新增产品如识别不满意，可增加一行覆盖显示名称，然后重新启动应用。

对于真实配置相同但标题相同的不同 ASIN，界面名称可能相同；ASIN 仍保留在后台以确保价格序列不是被错误合并。

## 当前数据质量清单

以下项目会随源文件更新而变化，并在看板“数据质量与口径说明”中动态展示：

1. 工作簿产品主表名称为 `84`，实际有 79 条产品记录。
2. 销量/销额明细含 55 个 ASIN，价格表含 60 个 ASIN，当前产品主表含 79 个 ASIN。
3. 5 个价格 ASIN 不在当前产品主表；其价格仍保留，品牌、标题和能可靠读取的容量来自价格表。
4. 24 个当前产品没有销量/销额历史，因此不会进入市场 KPI 或份额；当前快照未用来替代历史。
5. 24 个当前产品没有历史价格，因此不能绘制历史价格折线。
6. 2025–2026 价格表中有 204 个 0 欧元单元格，按缺失处理，不能当作免费产品。
7. 当前销量/销额明细中，存在大量空白缺失，也存在真实数值 0；看板对二者保留不同状态。空值不补 0。
8. 4 个价格产品的容量无法从主表或标题可靠识别，使用“未识别”容量段，不强制归入五个容量段之一。
9. `FOSSiBOT FBP1200` 原始容量为 39.1kWh，远高于其他产品；按源数据参与容量段和每 kWh 价格，建议业务复核该字段是否为扩展总容量。
10. `GreenSun Solar` 品牌字段对应的一条标题写明 `Marstek Venus E 3.0`；看板保留源品牌字段并显示质量提示。
11. 2026 年数据截至 11 月，环形图标注为 `2026 YTD (Nov)`，未生成 12 月价格、销量或销额。
12. 销量/销额 ASIN×月原始明细无重复键；品牌/容量段汇总页与明细重叠期间共 92 个年度/月份账面值核对一致。

## 数据校验结果

当前文件的关键控制数：

- 2025 Total Units：10,410
- 2025 Total Revenue：€12,762,391.85
- 2026 YTD Total Units：7,445
- 2026 YTD Total Revenue：€10,198,398.48
- 各品牌销量之和 = 市场总销量
- 各容量段销量之和 = 市场总销量
- 各品牌/容量段销量份额之和 = 100%

自动化测试覆盖总销量、总销额、品牌/容量段对账、容量边界、缺失与零值区分、固定色、全品牌/部分品牌线型、价格变化公式和 ASIN 不泄露。

## Germany 模块

Germany 模块保留原公开看板的实现，包括：

- 12 个重点品牌与 `Other brands` 的原有聚合规则。
- 品牌堆叠柱与 Ranking trend 两种图表模式。
- 容量段、双年度环形图、百分点变化和品牌 × 容量段热力图。
- 11 个目标竞品的价格折线、价格汇总 CSV 和原数据质量检查。

德国数据当前覆盖 2025-01 至 2026-10；法国数据截至 2026-11。两个看板不需要在同一个月结束，也不会为了对齐时间窗口而修改任何一方 KPI。

德国原测试已迁移到 `countries/germany/tests/`，统一入口另增加 France 默认展示、Germany 切换、切回 France，以及德国筛选器 rerun 测试。
