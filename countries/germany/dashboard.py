from __future__ import annotations

import html
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from .charts import (
    brand_performance_chart,
    capacity_performance_chart,
    donut_chart,
    heatmap_chart,
    price_line_chart,
    share_change_chart,
)
from .config import (
    APP_SUBTITLE,
    APP_TITLE,
    BRAND_COLORS,
    CAPACITY_SEGMENTS,
    DASHBOARD_CACHE_VERSION,
    DATA_PATH,
    FOCUS_BRANDS,
    OTHER_BRAND_LABEL,
    PLOTLY_CONFIG,
    PRICE_CHANGE_GREEN,
    PRICE_CHANGE_GREY,
    PRICE_CHANGE_RED,
    REPORT_YEARS,
    TARGET_PRICE_ASINS,
)
from .data_processing import (
    DashboardData,
    DashboardDataError,
    build_price_summary,
    filter_prices,
    filter_sales,
    heatmap_table,
    load_dashboard_data,
    market_share_table,
    monthly_dimension_pivot,
    prepare_brand_chart_data,
    share_change_table,
    summarize_sales,
)


CSS = """
<style>
:root {
  --navy: #0B2447;
  --blue: #1E5AA8;
  --ink: #142033;
  --muted: #667085;
  --surface: #FFFFFF;
  --canvas: #F3F6FA;
  --border: #E2E8F0;
}
html, body, [class*="css"] {
  font-family: "Segoe UI", Inter, Arial, sans-serif;
}
.stApp {
  background:
    radial-gradient(circle at 88% 0%, rgba(30, 90, 168, 0.08), transparent 28rem),
    linear-gradient(180deg, #F8FAFC 0%, #F3F6FA 100%);
}
.block-container {
  max-width: 1480px;
  padding-top: 1.2rem;
  padding-bottom: 3rem;
}
.hero {
  position: relative;
  overflow: hidden;
  border-radius: 20px;
  padding: 28px 32px 25px;
  background:
    linear-gradient(120deg, rgba(255,255,255,0.08), transparent 45%),
    linear-gradient(135deg, #0B2447 0%, #133D73 58%, #1E5AA8 100%);
  color: white;
  box-shadow: 0 16px 40px rgba(11, 36, 71, 0.18);
}
.hero::after {
  content: "";
  position: absolute;
  width: 310px;
  height: 310px;
  right: -70px;
  top: -170px;
  border-radius: 50%;
  border: 46px solid rgba(255,255,255,0.06);
}
.hero-kicker {
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #BFD4F2;
  font-weight: 700;
}
.hero h1 {
  margin: 0.34rem 0 0.16rem;
  font-size: clamp(1.9rem, 3.4vw, 3rem);
  letter-spacing: -0.035em;
  line-height: 1.12;
  color: #FFFFFF;
}
.hero-subtitle {
  color: #D7E5F7;
  font-size: 1rem;
  margin-bottom: 1.2rem;
}
.hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.hero-chip {
  border: 1px solid rgba(255,255,255,0.22);
  background: rgba(255,255,255,0.09);
  border-radius: 999px;
  padding: 6px 11px;
  font-size: 0.76rem;
  color: #F4F8FD;
}
.section-head {
  margin: 2.35rem 0 0.9rem;
  padding-top: 0.2rem;
}
.section-kicker {
  color: #1E5AA8;
  font-size: 0.72rem;
  letter-spacing: 0.13em;
  text-transform: uppercase;
  font-weight: 800;
}
.section-head h2 {
  color: #142033;
  margin: 0.26rem 0 0.2rem;
  font-size: 1.55rem;
  letter-spacing: -0.02em;
}
.section-head p {
  color: #667085;
  margin: 0;
  max-width: 960px;
  line-height: 1.55;
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin: 0.15rem 0 0.75rem;
}
.kpi-card {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-left: 4px solid #1E5AA8;
  border-radius: 14px;
  padding: 18px 20px;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.055);
}
.kpi-label {
  color: #667085;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.kpi-value {
  color: #142033;
  font-size: clamp(1.65rem, 3vw, 2.25rem);
  font-weight: 750;
  letter-spacing: -0.035em;
  line-height: 1.2;
  margin-top: 3px;
  white-space: nowrap;
}
.kpi-note {
  color: #8A96A8;
  font-size: 0.76rem;
  margin-top: 4px;
}
.chart-shell {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 16px;
  padding: 0.35rem 0.55rem 0.2rem;
  box-shadow: 0 9px 28px rgba(15, 23, 42, 0.045);
}
.insight {
  background: #F6F9FD;
  border: 1px solid #DCE7F4;
  border-radius: 12px;
  padding: 11px 14px;
  color: #344054;
  font-size: 0.88rem;
  line-height: 1.5;
}
.quality-ok {
  color: #238B57;
  font-weight: 700;
}
.quality-alert {
  color: #C24141;
  font-weight: 700;
}
.stMultiSelect [data-baseweb="tag"] {
  background-color: #E8F0FA !important;
  color: #0B3B74 !important;
}
.stButton > button, .stDownloadButton > button {
  border-radius: 9px;
  border-color: #CBD5E1;
}
div[data-testid="stExpander"] {
  border-color: #DCE4EE;
  border-radius: 13px;
  background: #FFFFFF;
}
div[data-testid="stDataFrame"] {
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  overflow: hidden;
}
.footer-note {
  border-top: 1px solid #DDE5EF;
  margin-top: 2.3rem;
  padding-top: 1rem;
  color: #8490A2;
  font-size: 0.76rem;
}
@media (max-width: 720px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; }
  .hero { padding: 22px 20px; }
  .kpi-grid { grid-template-columns: 1fr; }
}
</style>
"""
@st.cache_data(show_spinner=False)
def _cached_data(
    path: str,
    modified_at: float,
    cache_version: int,
) -> DashboardData:
    del modified_at
    del cache_version
    return load_dashboard_data(Path(path))


def format_units(value: float | None) -> str:
    return "—" if value is None or pd.isna(value) else f"{value:,.0f}"


def format_currency(value: float | None, compact: bool = False) -> str:
    if value is None or pd.isna(value):
        return "—"
    if compact:
        if abs(value) >= 1_000_000:
            return f"€{value / 1_000_000:,.2f}M"
        if abs(value) >= 1_000:
            return f"€{value / 1_000:,.1f}K"
    return f"€{value:,.0f}"


def section_header(kicker: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="section-head">
          <div class="section-kicker">{html.escape(kicker)}</div>
          <h2>{html.escape(title)}</h2>
          <p>{html.escape(description)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_cards(
    units: float | None,
    revenue: float | None,
    units_note: str,
    revenue_note: str,
) -> None:
    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-label">Total Units</div>
            <div class="kpi-value">{format_units(units)}</div>
            <div class="kpi-note">{html.escape(units_note)}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Total Revenue</div>
            <div class="kpi-value">{format_currency(revenue, compact=True)}</div>
            <div class="kpi-note">{html.escape(revenue_note)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def year_filter(key: str, default: str = "2026") -> list[int]:
    choice = st.segmented_control(
        "Year",
        options=["2026", "2025", "All years"],
        default=default,
        selection_mode="single",
        key=key,
        width="stretch",
    )
    if choice == "2025":
        return [2025]
    if choice == "2026":
        return [2026]
    return [2025, 2026]


def brand_options() -> list[str]:
    return [*FOCUS_BRANDS, OTHER_BRAND_LABEL]


def chart_container() -> st.delta_generator.DeltaGenerator:
    return st.container(border=False)


def render_header(data: DashboardData) -> None:
    latest = (
        data.quality.latest_month.strftime("%b %Y")
        if data.quality.latest_month is not None
        else "—"
    )
    source_updated = data.source_modified.strftime("%Y-%m-%d %H:%M")
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-kicker">Germany · Balcony Energy Storage</div>
          <h1>{html.escape(APP_TITLE)}</h1>
          <div class="hero-subtitle">{html.escape(APP_SUBTITLE)}</div>
          <div class="hero-meta">
            <span class="hero-chip">Data through {html.escape(latest)}</span>
            <span class="hero-chip">{data.quality.asin_count} ASINs</span>
            <span class="hero-chip">{data.quality.brand_count} source brands</span>
            <span class="hero-chip">Source updated {html.escape(source_updated)}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_brand_module(sales: pd.DataFrame) -> None:
    section_header(
        "01 · Brand Performance",
        "品牌销量与销额分析",
        "每月使用一根堆叠大柱展示销量，柱内按品牌分色。选择全部品牌时，右轴仅显示合计销额；"
        "减少品牌筛选后，右轴按品牌展示各自销额。",
    )
    controls = st.columns([1.05, 2.25, 1.65], gap="medium")
    with controls[0]:
        years = year_filter("brand_year")
    with controls[1]:
        selected_brands = st.multiselect(
            "Brand",
            options=brand_options(),
            default=brand_options(),
            key="brand_filter",
            help="12 个重点品牌单列；Other brands 为源数据中其余品牌的真实聚合。",
        )
    with controls[2]:
        mode = st.segmented_control(
            "Chart mode",
            options=["Stacked bars", "Ranking trend"],
            default="Stacked bars",
            selection_mode="single",
            key="brand_chart_mode",
            width="stretch",
        )

    filtered = filter_sales(
        sales,
        years=years,
        brands=selected_brands,
    )
    units, revenue = summarize_sales(filtered)
    year_text = "2025–2026" if len(years) == 2 else str(years[0])
    kpi_cards(
        units,
        revenue,
        f"{year_text} · 当前品牌筛选",
        f"{year_text} · 当前品牌筛选 · EUR",
    )

    if not selected_brands:
        st.warning("请至少选择一个品牌。")
        return
    if filtered["Units"].notna().sum() == 0 and filtered["Revenue"].notna().sum() == 0:
        st.info("当前筛选条件下没有可用的品牌销量或销额记录。")
        return

    totals = (
        filtered.groupby("Brand Display")[["Units", "Revenue"]]
        .sum(min_count=1)
        .sort_values("Units", ascending=False)
    )
    if not totals.empty and pd.notna(totals["Units"].iloc[0]):
        leader = totals.index[0]
        st.markdown(
            f'<div class="insight">当前筛选下销量最高的品牌为 <b>{html.escape(str(leader))}</b>，'
            f"销量 {format_units(float(totals['Units'].iloc[0]))} units。</div>",
            unsafe_allow_html=True,
        )

    chart_sales, chart_brands = prepare_brand_chart_data(
        filtered,
        selected_brands,
    )
    all_brands_selected = set(selected_brands) == set(brand_options())
    figure = brand_performance_chart(
        chart_sales,
        selected_brands=chart_brands,
        years=years,
        mode=mode or "Stacked bars",
        all_brands_selected=all_brands_selected,
    )
    st.plotly_chart(
        figure,
        width="stretch",
        config=PLOTLY_CONFIG,
        key="brand_chart",
    )
    st.caption(
        "全部品牌选中时只显示 Total Revenue 合计线；减少品牌后显示各品牌销额折线。"
        "排名模式切换为品牌月度销量排名折线。"
        "为减少视觉噪声，TSUN、Mentech、Jackery 在图中并入 Other brands，KPI 仍按完整筛选计算。"
        "未采集月份保留断点。"
    )


def render_capacity_module(sales: pd.DataFrame) -> None:
    section_header(
        "02 · Capacity Segment Analysis",
        "产品容量段销量与销额分析",
        "每月使用一根堆叠大柱展示销量，柱内按容量段分色。容量边界为 <2、2–3、3–4、4–5 和 >5kWh；"
        "2000Wh 归入 2–3kWh，5000Wh 归入 4–5kWh。",
    )
    controls = st.columns([1.05, 2.2, 1.65], gap="medium")
    with controls[0]:
        years = year_filter("capacity_year")
    with controls[1]:
        selected_brands = st.multiselect(
            "Brand",
            options=brand_options(),
            default=brand_options(),
            key="capacity_brand_filter",
        )
    with controls[2]:
        selected_segments = st.multiselect(
            "Capacity Segment",
            options=list(CAPACITY_SEGMENTS),
            default=list(CAPACITY_SEGMENTS),
            key="capacity_segment_filter",
        )

    filtered = filter_sales(
        sales,
        years=years,
        brands=selected_brands,
        capacity_segments=selected_segments,
    )
    units, revenue = summarize_sales(filtered)
    year_text = "2025–2026" if len(years) == 2 else str(years[0])
    kpi_cards(
        units,
        revenue,
        f"{year_text} · 当前品牌与容量段筛选",
        f"{year_text} · 当前品牌与容量段筛选 · EUR",
    )

    if not selected_brands or not selected_segments:
        st.warning("请至少选择一个品牌和一个容量段。")
        return
    if filtered["Units"].notna().sum() == 0 and filtered["Revenue"].notna().sum() == 0:
        st.info("当前筛选条件下没有可用的容量段记录。")
        return

    figure = capacity_performance_chart(
        filtered,
        selected_segments=selected_segments,
        years=years,
    )
    st.plotly_chart(
        figure,
        width="stretch",
        config=PLOTLY_CONFIG,
        key="capacity_chart",
    )
    st.caption(
        "销量使用左轴堆叠柱，销额折线使用右轴。点击图例隐藏或显示容量段；悬停查看月度明细。"
    )


def render_market_share_module(sales: pd.DataFrame) -> None:
    section_header(
        "03 · Market Share Analysis",
        "市场份额及结构变化分析",
        "对比 2025 年与 2026 年年初至今结构。品牌维度包含 12 个重点品牌及 Other brands，容量段维度覆盖全部 ASIN；环形图中心显示当年总量。",
    )
    controls = st.columns([1, 1], gap="medium")
    with controls[0]:
        dimension_label = st.segmented_control(
            "分析维度",
            options=["Brand", "Capacity Segment"],
            default="Brand",
            selection_mode="single",
            key="share_dimension",
            width="stretch",
        )
    with controls[1]:
        metric = st.segmented_control(
            "分析指标",
            options=["Units", "Revenue"],
            default="Units",
            selection_mode="single",
            key="share_metric",
            width="stretch",
        )

    dimension = "Brand Display" if dimension_label == "Brand" else "Capacity Segment"
    year_2026_totals = (
        sales[sales["Year"] == 2026]
        .groupby(dimension)["Units"]
        .sum(min_count=1)
        .sort_values(ascending=False)
    )
    if dimension == "Brand Display":
        categories = [
            *[brand for brand in year_2026_totals.index if brand in FOCUS_BRANDS],
            OTHER_BRAND_LABEL,
        ]
    else:
        categories = list(CAPACITY_SEGMENTS)

    left, right = st.columns(2, gap="large")
    tables: dict[int, pd.DataFrame] = {}
    for column, year in zip((left, right), (2025, 2026), strict=True):
        table = market_share_table(
            sales,
            year=year,
            dimension=dimension,
            metric=metric or "Units",
            categories=categories,
        )
        tables[year] = table
        year_sales = sales[sales["Year"] == year]
        total_units, total_revenue = summarize_sales(year_sales)
        with column:
            figure = donut_chart(
                table,
                year=year,
                dimension=dimension,
                metric=metric or "Units",
                total_units=total_units,
                total_revenue=total_revenue,
            )
            st.plotly_chart(
                figure,
                width="stretch",
                config=PLOTLY_CONFIG,
                key=f"share_donut_{year}",
            )

    st.caption(
        "2026 年数据截至 10 月，为年初至今份额；两年比较使用份额和百分点变化，避免把未完整年份与全年直接比较。"
    )
    comparison = share_change_table(
        sales,
        dimension=dimension,
        metric=metric or "Units",
        categories=categories,
    )
    change_figure = share_change_chart(comparison, metric=metric or "Units")
    st.plotly_chart(
        change_figure,
        width="stretch",
        config=PLOTLY_CONFIG,
        key="share_change_chart",
    )
    valid_changes = comparison.dropna(subset=["Change pp"])
    if not valid_changes.empty:
        leader = valid_changes.sort_values("Change pp", ascending=False).iloc[0]
        laggard = valid_changes.sort_values("Change pp", ascending=True).iloc[0]
        st.markdown(
            f'<div class="insight">份额增幅最大：<b>{html.escape(str(leader["Category"]))}</b> '
            f'({leader["Change pp"]:+.1f}pp)；份额降幅最大：'
            f'<b>{html.escape(str(laggard["Category"]))}</b> '
            f'({laggard["Change pp"]:+.1f}pp)。绿色为上升，红色为下降。</div>',
            unsafe_allow_html=True,
        )

    st.markdown("#### 品牌 × 容量段结构")
    heat_controls = st.columns([1, 1], gap="medium")
    with heat_controls[0]:
        heat_year_label = st.segmented_control(
            "Heatmap year",
            options=["2026", "2025"],
            default="2026",
            selection_mode="single",
            key="heatmap_year",
            width="stretch",
        )
    with heat_controls[1]:
        heat_metric_label = st.segmented_control(
            "Heatmap metric",
            options=["Units", "Revenue"],
            default="Units",
            selection_mode="single",
            key="heatmap_metric",
            width="stretch",
        )

    heat_year = int(heat_year_label or "2026")
    heat_metric = heat_metric_label or "Units"
    brand_scope = sales[sales["Year"] == heat_year]
    brand_order = (
        brand_scope.groupby("Brand Display")["Units"]
        .sum(min_count=1)
        .sort_values(ascending=False)
    )
    heat_brands = [
        *[brand for brand in brand_order.index if brand in FOCUS_BRANDS],
        OTHER_BRAND_LABEL,
    ]
    matrix = heatmap_table(
        sales,
        year=heat_year,
        metric=heat_metric,
        brands=heat_brands,
        segments=CAPACITY_SEGMENTS,
    )
    heat_figure = heatmap_chart(matrix, metric=heat_metric, year=heat_year)
    st.plotly_chart(
        heat_figure,
        width="stretch",
        config=PLOTLY_CONFIG,
        key="brand_capacity_heatmap",
    )
    st.caption(
        "热力图按当前年份与指标展示品牌在各容量段的真实聚合值；空白表示没有可用数据。"
    )


def style_price_table(frame: pd.DataFrame) -> pd.io.formats.style.Styler:
    def change_color(value: object) -> str:
        if pd.isna(value):
            return f"color: {PRICE_CHANGE_GREY}"
        if value > 0:
            return f"color: {PRICE_CHANGE_RED}; font-weight: 650"
        if value < 0:
            return f"color: {PRICE_CHANGE_GREEN}; font-weight: 650"
        return f"color: {PRICE_CHANGE_GREY}"

    shown = frame.rename(
        columns={
            "Capacity Wh": "Capacity (Wh)",
            "Price per kWh": "Price per kWh (€)",
        }
    )
    return (
        shown.style.format(
            {
                "Capacity (Wh)": "{:,.0f}",
                "Average Price": "€{:,.2f}",
                "Minimum Price": "€{:,.2f}",
                "Maximum Price": "€{:,.2f}",
                "Latest Price": "€{:,.2f}",
                "Previous Month Price": "€{:,.2f}",
                "Price Change (%)": "{:+.2f}%",
                "Price per kWh (€)": "€{:,.2f}",
                "Latest Month": "{:%Y-%m}",
            },
            na_rep="—",
        )
        .map(change_color, subset=["Price Change (%)"])
    )


def render_price_module(data: DashboardData) -> None:
    section_header(
        "04 · Price Tracking",
        "核心竞品价格变化分析",
        "追踪 11 个核心产品的逐月真实售价，以品牌、系列名称和容量 Wh 识别产品。"
        "缺失月份保留断点，不插值、不补零。",
    )
    catalog = data.price_products.copy()
    controls = st.columns([1.3, 1.0, 1.1, 1.8], gap="medium")
    with controls[0]:
        years = year_filter("price_year")
    valid_catalog = data.prices[data.prices["Year"].isin(years)]
    available_asins = set(valid_catalog["ASIN"].unique())
    catalog_for_filters = catalog[catalog["ASIN"].isin(available_asins)]
    with controls[1]:
        price_brands = st.multiselect(
            "Brand",
            options=catalog_for_filters["Brand"].drop_duplicates().tolist(),
            default=catalog_for_filters["Brand"].drop_duplicates().tolist(),
            key="price_brand_filter",
        )
    with controls[2]:
        price_segments = st.multiselect(
            "Capacity Segment",
            options=[
                segment
                for segment in CAPACITY_SEGMENTS
                if segment in catalog_for_filters["Capacity Segment"].unique()
            ],
            default=[
                segment
                for segment in CAPACITY_SEGMENTS
                if segment in catalog_for_filters["Capacity Segment"].unique()
            ],
            key="price_segment_filter",
        )

    catalog_filtered = catalog_for_filters[
        catalog_for_filters["Brand"].isin(price_brands)
        & catalog_for_filters["Capacity Segment"].isin(price_segments)
    ]
    product_options = catalog_filtered["Product Label"].drop_duplicates().tolist()
    label_to_asins = (
        catalog_filtered.groupby("Product Label")["ASIN"]
        .apply(list)
        .to_dict()
    )
    asin_key_suffix = "_".join(
        [*sorted(price_brands), *sorted(price_segments)]
    ).replace(" ", "_")
    with controls[3]:
        selected_product_labels = st.multiselect(
            "Product / Series",
            options=product_options,
            default=product_options,
            key=f"price_product_filter_{asin_key_suffix}",
            help="显示品牌、系列和容量，不显示 ASIN。",
        )
    selected_asins = [
        asin
        for label in selected_product_labels
        for asin in label_to_asins.get(label, [])
    ]

    price_data = filter_prices(
        data.prices,
        years=years,
        brands=price_brands,
        capacity_segments=price_segments,
        asins=selected_asins,
    )
    summary = build_price_summary(
        price_data,
        catalog,
        selected_brands=price_brands,
        selected_segments=price_segments,
        selected_asins=selected_asins,
    )

    products_with_price = int(summary["Latest Price"].notna().sum())
    average_latest = (
        float(summary["Latest Price"].mean())
        if summary["Latest Price"].notna().any()
        else None
    )
    latest_month = (
        summary["Latest Month"].max()
        if summary["Latest Month"].notna().any()
        else None
    )
    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-label">Products with Price</div>
            <div class="kpi-value">{products_with_price} / {len(summary)}</div>
            <div class="kpi-note">当前筛选内存在真实价格记录的产品</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Average Latest Price</div>
            <div class="kpi-value">{format_currency(average_latest)}</div>
            <div class="kpi-note">最新可用价格均值 · {latest_month.strftime('%b %Y') if pd.notna(latest_month) else '—'}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not price_brands or not price_segments or not selected_product_labels:
        st.warning("请至少选择一个品牌、容量段和产品系列。")
        return
    if price_data["Price"].notna().sum() == 0:
        st.info("当前筛选条件下没有可用的历史价格记录。")
        return

    line_figure = price_line_chart(
        price_data,
        product_catalog=catalog,
        selected_asins=selected_asins,
    )
    st.plotly_chart(
        line_figure,
        width="stretch",
        config=PLOTLY_CONFIG,
        key="price_line_chart",
    )
    st.caption(
        "图例和悬浮信息显示品牌、系列、容量、月份、售价和 €/kWh；图例可单独显示或隐藏产品。"
    )

    st.markdown("#### 产品价格汇总")
    table_columns = [
        "Brand",
        "Series",
        "Product Name",
        "Capacity Wh",
        "Capacity Segment",
        "Average Price",
        "Minimum Price",
        "Maximum Price",
        "Latest Month",
        "Latest Price",
        "Previous Month Price",
        "Price Change (%)",
        "Price per kWh",
    ]
    st.dataframe(
        style_price_table(summary[table_columns]),
        width="stretch",
        hide_index=True,
        height=430,
        column_config={
            "Product Name": st.column_config.TextColumn(
                "Product Name",
                width="large",
            ),
            "Price Change (%)": st.column_config.TextColumn(
                "Price Change (%)",
                width="small",
                help="涨价为红色，降价为绿色；缺失上月价格时显示 —。",
            ),
        },
    )
    st.caption(
        "Price Change 使用最新可用月份与前一个自然月比较。若前一个自然月缺失，变化率留空。"
        "€/kWh 使用最新售价除以容量（kWh）。"
    )

    missing_price = summary.loc[
        summary["Latest Price"].isna(),
        ["Brand", "Series", "Capacity Wh"],
    ]
    if not missing_price.empty:
        missing_text = "、".join(
            f"{row.Brand} {row.Series} {row._3:,.0f}Wh"
            for row in missing_price.itertuples()
        )
        st.warning(f"以下产品在当前筛选内没有可用价格记录：{missing_text}")

    export = summary.drop(columns=["ASIN"]).copy()
    export["Latest Month"] = export["Latest Month"].dt.strftime("%Y-%m")
    st.download_button(
        "下载当前价格汇总 CSV",
        data=export.to_csv(index=False).encode("utf-8-sig"),
        file_name="germany_balcony_price_summary.csv",
        mime="text/csv",
        width="content",
    )


def render_quality(data: DashboardData) -> None:
    quality = data.quality
    section_header(
        "Data Quality",
        "数据质量与口径检查",
        "检查结果直接影响 KPI 与图表解释。所有缺失值保持缺失状态，真实零值保留；0€ 价格不作为有效售价。",
    )
    status = (
        '<span class="quality-ok">通过</span>'
        if quality.capacity_reconciles
        else '<span class="quality-alert">存在差异</span>'
    )
    status_markup = f"""
    <div class="kpi-grid" style="grid-template-columns: repeat(3, minmax(0,1fr));">
      <div class="kpi-card">
        <div class="kpi-label">ASIN Coverage</div>
        <div class="kpi-value">{quality.asin_count}</div>
        <div class="kpi-note">{quality.focus_brand_count} 个重点品牌 + {quality.other_brand_count} 个其他品牌</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Capacity Reconciliation</div>
        <div class="kpi-value">{status}</div>
        <div class="kpi-note">ASIN 明细 vs 容量段汇总 · 最大差异 {quality.capacity_max_diff:,.0f}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Price Coverage</div>
        <div class="kpi-value">{quality.price_products_found} / {quality.price_products_expected}</div>
        <div class="kpi-note">核心产品存在价格文件行 · 缺失月份 {quality.price_missing_cells}</div>
      </div>
    </div>
    """
    st.markdown(status_markup, unsafe_allow_html=True)

    issues = pd.DataFrame(quality.issues)
    st.dataframe(
        issues,
        width="stretch",
        hide_index=True,
        column_config={
            "Severity": st.column_config.TextColumn("Severity", width="small"),
            "Area": st.column_config.TextColumn("Area", width="small"),
            "Finding": st.column_config.TextColumn("Finding", width="large"),
            "Impact": st.column_config.TextColumn("Impact", width="medium"),
            "Handling": st.column_config.TextColumn("Handling", width="large"),
        },
    )

    with st.expander("查看字段映射、清洗规则与详细对账"):
        mapping = pd.DataFrame(
            [
                ["产品历史月销量", "ASIN", "ASIN"],
                ["产品历史月销量", "brand", "Brand → Brand Display"],
                ["产品历史月销量", "容量（文本）+ 容量（数值）", "Capacity Wh"],
                ["产品历史月销量", "容量段", "源标签校验；看板按业务边界重算 Capacity Segment"],
                ["产品历史月销量", "商品标题", "Product Name"],
                ["产品历史月销量", "2025-01 … 2026-10", "Date / Year / Month Number / Units"],
                ["历史月销售额", "2025-01(€) … 2026-10(€)", "Revenue"],
                ["历史月价格", "2025-01(€) … 2026-10(€)", "Price"],
                ["按品牌，25/26月销量", "求和项:年份-月份", "品牌汇总对账"],
                ["按容量段，25/26月销量", "求和项:年份-月份", "容量段汇总对账"],
            ],
            columns=["Sheet", "Source Field", "Dashboard Field / Use"],
        )
        st.dataframe(mapping, width="stretch", hide_index=True)

        st.markdown(
            """
**清洗规则**

- 统一品牌大小写与常见拼写；12 个重点品牌单列，其余真实品牌聚合为 `Other brands`。
- 容量文本支持 `Wh`、`kWh` 和纯数字；统一换算为 Wh。
- 容量段使用左闭右开边界：`<2000`、`[2000,3000)`、`[3000,4000)`、`[4000,5000]`、`>5000`。
- 日期从 `YYYY-MM` 字段解析为真实月份日期，按自然时间排序。
- ASIN × 月份重复记录会阻止计算并提示，不直接删除。
- 缺失销量、销额、价格保持为空；求和时只汇总有效值，不填 0。
- 价格 ≤ €0 视为不可用价格，不进入价格折线与统计，但原始异常记录数量保留在质量检查中。
            """
        )

        st.markdown("**源工作表**")
        st.code("\n".join(quality.source_sheets), language="text")

        if not quality.brand_pivot_mismatch_rows.empty:
            st.markdown("**品牌汇总表与 ASIN 明细月度差异**")
            mismatch = quality.brand_pivot_mismatch_rows.copy()
            mismatch["Date"] = mismatch["Date"].dt.strftime("%Y-%m")
            mismatch = mismatch.rename(
                columns={
                    "Brand sheet": "品牌汇总表 Units",
                    "ASIN detail": "ASIN 明细 Units",
                    "Difference": "差异",
                }
            )
            st.dataframe(mismatch, width="stretch", hide_index=True)
            st.caption(
                "看板以 ASIN 明细为统一主口径，原因是其容量段汇总与全市场月度容量段表逐月一致。"
            )


def main() -> None:
    # Re-inject on every Streamlit rerun. Module-level CSS is lost when a
    # cached country module is reused after switching countries.
    st.markdown(CSS, unsafe_allow_html=True)

    if not DATA_PATH.exists():
        st.error(f"未找到数据文件：{DATA_PATH}")
        st.stop()

    try:
        data = _cached_data(
            str(DATA_PATH),
            DATA_PATH.stat().st_mtime,
            DASHBOARD_CACHE_VERSION,
        )
    except DashboardDataError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"加载数据时发生未预期错误：{exc}")
        st.stop()

    render_header(data)

    render_brand_module(data.sales)
    render_capacity_module(data.sales)
    render_market_share_module(data.sales)
    render_price_module(data)
    render_quality(data)

    st.markdown(
        f"""
        <div class="footer-note">
          数据源：{html.escape(data.source_path.name)} · 最近文件更新时间：
          {data.source_modified.strftime('%Y-%m-%d %H:%M')} · KPI、图表和价格表均由同一 Excel 实时计算。
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
