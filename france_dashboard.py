from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

from charts import (
    brand_segment_heatmap,
    market_share_donut,
    price_history_chart,
    share_change_chart,
    stacked_units_revenue_chart,
)
from config import (
    DASHBOARD_SUBTITLE,
    DASHBOARD_TITLE,
    DATA_SCOPE,
    NEGATIVE_COLOR,
    NEUTRAL_COLOR,
    POSITIVE_COLOR,
    SEGMENT_COLORS,
    SEGMENT_ORDER,
    YEAR_OPTIONS,
    UNKNOWN_SEGMENT,
    resolve_source_file,
)
from data_processing import (
    DashboardData,
    aggregate_monthly,
    aggregate_share,
    brand_color_map,
    expected_year_label,
    filter_market,
    filter_prices,
    format_capacity,
    heatmap_data,
    kpis,
    load_dashboard_data,
    period_to_date,
    price_summary,
    share_change,
    top_price_products,
)


if __name__ == "__main__":
    st.set_page_config(
        page_title=DASHBOARD_TITLE,
        page_icon="◫",
        layout="wide",
        initial_sidebar_state="collapsed",
    )


PLOTLY_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "scrollZoom": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "balcony-storage-dashboard",
        "scale": 2,
    },
}


APP_CSS = """
<style>
:root {
    --canvas: #f4f6f8;
    --surface: #ffffff;
    --border: #dfe5e9;
    --text: #24313a;
    --muted: #66747d;
    --accent: #315f6b;
    --accent-soft: #edf4f5;
}
html, body, [class*="css"] {
    font-family: Inter, "Segoe UI", Arial, sans-serif;
}
[data-testid="stAppViewContainer"] {
    background: var(--canvas);
    color: var(--text);
}
[data-testid="stHeader"] {
    background: rgba(244, 246, 248, 0.9);
}
.block-container {
    max-width: 1480px;
    padding-top: 1.6rem;
    padding-bottom: 4rem;
}
.hero {
    position: relative;
    overflow: hidden;
    padding: 30px 34px 27px;
    margin-bottom: 18px;
    border: 1px solid var(--border);
    border-radius: 18px;
    background:
        radial-gradient(circle at 92% 20%, rgba(84, 129, 137, 0.13), transparent 26%),
        linear-gradient(135deg, #ffffff 0%, #f8fafb 100%);
    box-shadow: 0 10px 28px rgba(37, 54, 65, 0.055);
}
.hero-kicker {
    color: var(--accent);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin-bottom: 10px;
}
.hero h1 {
    color: var(--text);
    font-size: clamp(29px, 3vw, 43px);
    line-height: 1.13;
    letter-spacing: -0.035em;
    margin: 0 0 8px;
}
.hero-subtitle {
    color: var(--muted);
    font-size: 16px;
    margin-bottom: 19px;
}
.meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
}
.meta-pill {
    padding: 7px 11px;
    border: 1px solid #dce4e7;
    border-radius: 999px;
    color: #4d5e67;
    background: rgba(255,255,255,0.78);
    font-size: 12px;
}
.module-heading {
    display: flex;
    align-items: flex-start;
    gap: 15px;
    margin: 15px 0 12px;
}
.module-number {
    flex: 0 0 auto;
    display: flex;
    justify-content: center;
    align-items: center;
    width: 36px;
    height: 36px;
    margin-top: 2px;
    border-radius: 10px;
    color: #ffffff;
    background: var(--accent);
    font-size: 13px;
    font-weight: 700;
}
.module-eyebrow {
    color: var(--accent);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.10em;
    text-transform: uppercase;
}
.module-title {
    color: var(--text);
    font-size: 24px;
    font-weight: 700;
    line-height: 1.25;
    margin: 2px 0 4px;
}
.module-description {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.55;
    max-width: 1000px;
}
[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: var(--border);
    border-radius: 16px;
    background: var(--surface);
    box-shadow: 0 5px 18px rgba(34, 51, 61, 0.035);
}
.kpi-card {
    min-height: 116px;
    padding: 21px 23px 18px;
    border: 1px solid var(--border);
    border-radius: 15px;
    background: linear-gradient(145deg, #ffffff, #f9fbfb);
}
.kpi-label {
    color: var(--muted);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.035em;
    margin-bottom: 10px;
}
.kpi-value {
    color: var(--text);
    font-size: clamp(27px, 3vw, 38px);
    font-weight: 700;
    letter-spacing: -0.035em;
    line-height: 1.1;
    white-space: nowrap;
}
.kpi-context {
    color: #7a878f;
    font-size: 11px;
    margin-top: 9px;
}
.chart-heading {
    color: var(--text);
    font-size: 17px;
    font-weight: 700;
    margin: 2px 0 1px;
}
.chart-note {
    color: var(--muted);
    font-size: 12px;
    line-height: 1.55;
    margin: 0 0 6px;
}
.section-divider {
    height: 1px;
    margin: 30px 0 19px;
    background: linear-gradient(90deg, #d9e1e5, rgba(217,225,229,0));
}
.quality-row {
    padding: 10px 0;
    border-bottom: 1px solid #edf0f2;
}
.quality-title {
    color: var(--text);
    font-size: 13px;
    font-weight: 650;
}
.quality-detail {
    color: var(--muted);
    font-size: 12px;
    line-height: 1.55;
    margin-top: 3px;
}
.quality-level {
    display: inline-block;
    padding: 2px 7px;
    margin-right: 7px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 700;
    vertical-align: 1px;
}
.level-critical {color: #842f2f; background: #f8e5e5;}
.level-warning {color: #7a5427; background: #f8edda;}
.level-notice {color: #3f6470; background: #e8f1f3;}
.small-note {
    color: var(--muted);
    font-size: 11px;
}
[data-testid="stMultiSelect"] label,
[data-testid="stRadio"] label,
[data-testid="stSelectbox"] label,
[data-testid="stToggle"] label {
    color: #46565f;
    font-size: 12px;
    font-weight: 600;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] {
    min-height: 26px;
    border: 1px solid #d7e2e4 !important;
    border-radius: 7px !important;
    background: #edf3f4 !important;
    color: #304e57 !important;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] span {
    color: #304e57 !important;
    font-size: 11px !important;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] svg {
    fill: #5b7078 !important;
}
[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
}
</style>
"""


st.markdown(APP_CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner="正在读取并校验 Excel 数据…")
def load_cached_data(path: str, modified_ns: int) -> DashboardData:
    del modified_ns
    return load_dashboard_data(Path(path))


def section_header(
    number: str,
    eyebrow: str,
    title: str,
    description: str,
) -> None:
    st.markdown(
        f"""
        <div class="module-heading">
            <div class="module-number">{number}</div>
            <div>
                <div class="module-eyebrow">{eyebrow}</div>
                <div class="module-title">{title}</div>
                <div class="module-description">{description}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def chart_header(title: str, note: str = "") -> None:
    note_html = f'<div class="chart-note">{note}</div>' if note else ""
    st.markdown(
        f'<div class="chart-heading">{title}</div>{note_html}',
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, context: str) -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-context">{context}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(metrics: dict[str, float], scope: str) -> None:
    left, right = st.columns(2, gap="medium")
    with left:
        units = "—" if pd.isna(metrics["units"]) else f"{metrics['units']:,.0f}"
        kpi_card(
            "Total Units",
            units,
            f"{scope} · 仅汇总有效销量记录",
        )
    with right:
        revenue = (
            "—"
            if pd.isna(metrics["revenue"])
            else f"€{metrics['revenue']:,.0f}"
        )
        kpi_card(
            "Total Revenue",
            revenue,
            f"{scope} · 仅汇总有效销售额记录",
        )


def year_selection(label: str, key: str) -> tuple[str, list[int]]:
    choice = st.selectbox(
        label,
        YEAR_OPTIONS,
        index=0,
        key=key,
        format_func=lambda value: "全部年份" if value == "全部年份" else str(value),
    )
    years = [2025, 2026] if choice == "全部年份" else [int(choice)]
    return str(choice), years


def selected_scope_text(
    year_choice: str, brands: list[str], all_brand_count: int
) -> str:
    brand_text = (
        "全部品牌"
        if len(brands) == all_brand_count
        else f"{len(brands)} 个品牌"
    )
    return f"{year_choice} · {brand_text}"


def filter_signature(*values: object) -> str:
    text = "|".join(
        ",".join(sorted(map(str, value))) if isinstance(value, (list, tuple, set)) else str(value)
        for value in values
    )
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:10]


def quality_panel(data: DashboardData) -> None:
    issue_count = len(data.quality_issues)
    with st.expander(f"数据质量与口径说明 · {issue_count} 项", expanded=False):
        st.success("；".join(data.validation_notes), icon="✅")
        if not data.quality_issues:
            st.caption("未发现需要单独提示的数据质量事项。")
            return
        order = {"critical": 0, "warning": 1, "notice": 2}
        labels = {"critical": "高", "warning": "中", "notice": "说明"}
        for issue in sorted(
            data.quality_issues, key=lambda item: order.get(item.level, 9)
        ):
            level_label = labels.get(issue.level, "说明")
            st.markdown(
                f"""
                <div class="quality-row">
                    <div class="quality-title">
                        <span class="quality-level level-{issue.level}">{level_label}</span>
                        {issue.title}
                    </div>
                    <div class="quality-detail">{issue.detail}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.caption("完整口径、字段映射及数据问题清单见项目 README.md。")


try:
    source_path = resolve_source_file()
    data = load_cached_data(
        str(source_path), source_path.stat().st_mtime_ns
    )
except Exception as exc:
    st.error(f"数据加载失败：{exc}")
    st.stop()


brand_colors = brand_color_map(data.market_brands + data.price_brands)

latest_market_date = (
    period_to_date(data.latest_market_month).strftime("%Y-%m")
    if data.latest_market_month
    else "—"
)
source_modified = data.source_modified.strftime("%Y-%m-%d %H:%M")

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-kicker">{DATA_SCOPE} · Market Intelligence</div>
        <h1>{DASHBOARD_TITLE}</h1>
        <div class="hero-subtitle">{DASHBOARD_SUBTITLE}</div>
        <div class="meta-row">
            <span class="meta-pill">数据截至 {latest_market_date}</span>
            <span class="meta-pill">文件更新 {source_modified}</span>
            <span class="meta-pill">来源 {data.source_path.name}</span>
            <span class="meta-pill">金额单位 € · 容量单位 kWh</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

quality_panel(data)

# ---------------------------------------------------------------------------
# Module 1
# ---------------------------------------------------------------------------
section_header(
    "01",
    "Brand Performance",
    "品牌销量与销额分析",
    "按自然月观察市场总量与品牌贡献。全部品牌状态下，销量采用单柱堆叠，销额仅展示一条市场总额线；选择部分品牌时，再拆分品牌销额线。",
)

with st.container(border=True):
    filter_left, filter_right = st.columns([1.0, 4.6], gap="medium")
    with filter_left:
        year_choice_1, years_1 = year_selection("年份", "m1_year")
    with filter_right:
        brands_1 = st.multiselect(
            "品牌",
            options=data.market_brands,
            default=data.market_brands,
            key="m1_brands",
            placeholder="选择品牌",
        )

    if not brands_1:
        st.warning("请至少选择一个品牌。")
    else:
        frame_1 = filter_market(data, years_1, brands_1)
        metrics_1 = kpis(frame_1)
        render_kpis(
            metrics_1,
            selected_scope_text(
                year_choice_1, brands_1, len(data.market_brands)
            ),
        )
        st.write("")
        all_brands_selected = set(brands_1) == set(data.market_brands)
        line_mode = "market_total" if all_brands_selected else "per_category"
        monthly_1 = aggregate_monthly(frame_1, "brand", years_1)
        chart_header(
            "品牌月度销量与销额",
            "柱形：月度销量（堆叠，Units）；折线：月度销售额（€）。"
            "图例可隐藏数据系列；右上角工具栏支持缩放、平移、重置和导出。"
            if all_brands_selected
            else "当前为部分品牌视图：柱形保留月度堆叠，销额按所选品牌分别展示。",
        )
        figure_1 = stacked_units_revenue_chart(
            monthly_1,
            category_order=brands_1,
            colors=brand_colors,
            years=years_1,
            category_label="品牌",
            line_mode=line_mode,
        )
        st.plotly_chart(
            figure_1,
            width="stretch",
            config=PLOTLY_CONFIG,
            key="chart_brand_monthly",
        )
        st.caption(
            f"有效销量单元 {metrics_1['unit_records']:,} 个；"
            f"有效销额单元 {metrics_1['revenue_records']:,} 个；"
            f"二者均缺失的 ASIN×月记录 {metrics_1['missing_both']:,} 个，未补零。"
        )

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Module 2
# ---------------------------------------------------------------------------
section_header(
    "02",
    "Capacity Segment Analysis",
    "容量段销量与销额分析",
    "容量边界严格互斥：2,000Wh、3,000Wh、4,000Wh 和 5,000Wh 分别归入其上限区间；5,000Wh 纳入 4–5kWh，>5,000Wh 纳入 >5kWh。",
)

with st.container(border=True):
    filter_left, filter_right = st.columns([1.0, 4.6], gap="medium")
    with filter_left:
        year_choice_2, years_2 = year_selection("年份", "m2_year")
    with filter_right:
        brands_2 = st.multiselect(
            "品牌",
            options=data.market_brands,
            default=data.market_brands,
            key="m2_brands",
            placeholder="选择品牌",
        )

    if not brands_2:
        st.warning("请至少选择一个品牌。")
    else:
        frame_2 = filter_market(data, years_2, brands_2)
        metrics_2 = kpis(frame_2)
        render_kpis(
            metrics_2,
            selected_scope_text(
                year_choice_2, brands_2, len(data.market_brands)
            ),
        )
        st.write("")
        monthly_2 = aggregate_monthly(frame_2, "capacity_segment", years_2)
        chart_header(
            "容量段月度销量与销额",
            "每月为一个完整堆叠柱，柱内展示五个容量段的销量贡献；右侧折线展示各容量段销售额。空白或无记录月份不补零。",
        )
        figure_2 = stacked_units_revenue_chart(
            monthly_2,
            category_order=SEGMENT_ORDER,
            colors=SEGMENT_COLORS,
            years=years_2,
            category_label="容量段",
            line_mode="per_category",
        )
        st.plotly_chart(
            figure_2,
            width="stretch",
            config=PLOTLY_CONFIG,
            key="chart_capacity_monthly",
        )
        segment_sum = (
            frame_2.groupby("capacity_segment", dropna=False)["units"]
            .agg(lambda values: values.sum(min_count=1))
            .reindex(SEGMENT_ORDER)
        )
        st.caption(
            "容量段合计核对："
            + " · ".join(
                f"{segment} {value:,.0f}"
                for segment, value in segment_sum.items()
                if pd.notna(value)
            )
        )

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Module 3
# ---------------------------------------------------------------------------
section_header(
    "03",
    "Market Share Analysis",
    "品牌及容量段市场份额分析",
    "比较 2025 年与 2026 年截至最新数据的结构变化。份额变化以百分点（pp）计算；当任一年度缺少该维度记录时，不把缺失误当作 0%，也不计算变化。",
)

with st.container(border=True):
    col_year, col_dimension, col_metric, col_space = st.columns([1.05, 1.55, 1.55, 2])
    with col_year:
        comparison = st.radio(
            "年份对比",
            ["两个年份", "2025", "2026"],
            index=0,
            horizontal=True,
            key="m3_comparison",
        )
    with col_dimension:
        dimension = st.radio(
            "分析维度",
            ["Brand", "Capacity Segment"],
            index=0,
            horizontal=True,
            key="m3_dimension",
            format_func=lambda value: "品牌" if value == "Brand" else "容量段",
        )
    with col_metric:
        metric = st.radio(
            "分析指标",
            ["Units Share", "Revenue Share"],
            index=0,
            horizontal=True,
            key="m3_metric",
            format_func=lambda value: "销量占比" if value == "Units Share" else "销额占比",
        )

    dimension_column = "brand" if dimension == "Brand" else "capacity_segment"
    dimension_colors = (
        brand_colors if dimension == "Brand" else SEGMENT_COLORS
    )
    years_to_show = [2025, 2026] if comparison == "两个年份" else [int(comparison)]
    donut_columns = st.columns(len(years_to_show), gap="large")
    share_frames: dict[int, pd.DataFrame] = {}
    for column, year in zip(donut_columns, years_to_show, strict=False):
        share_frames[year] = aggregate_share(data.market_long, year, dimension)
        with column:
            year_label = expected_year_label(data, year)
            chart_header(
                f"{year_label} · {'品牌' if dimension == 'Brand' else '容量段'}"
            )
            st.plotly_chart(
                market_share_donut(
                    share_frames[year],
                    year,
                    dimension,
                    metric,
                    dimension_colors,
                ),
                width="stretch",
                config=PLOTLY_CONFIG,
                key=f"donut_{year}_{dimension}_{metric}",
            )

    if comparison == "两个年份":
        st.write("")
        chart_header(
            "市场份额变化",
            "2026 − 2025，单位：百分点（pp）。按变化绝对值从大到小排序；绿色为份额上升，红色为份额下降，灰色为变化小于 0.05pp。",
        )
        change = share_change(data.market_long, dimension, metric)
        if change.empty:
            st.info("没有可比较的两年份额记录。")
        else:
            st.plotly_chart(
                share_change_chart(change, dimension, metric),
                width="stretch",
                config=PLOTLY_CONFIG,
                key=f"share_change_{dimension}_{metric}",
            )
    else:
        st.info("份额变化图需要同时选择 2025 和 2026 两个年份。")

    st.write("")
    with st.expander("品牌 × 容量段热力图", expanded=True):
        heat_left, heat_right, heat_note = st.columns([1, 1, 3])
        with heat_left:
            heat_year = st.radio(
                "热力图年份",
                [2025, 2026],
                index=1,
                horizontal=True,
                key="m3_heat_year",
            )
        with heat_right:
            heat_metric = st.radio(
                "热力图指标",
                ["Units", "Revenue"],
                index=0,
                horizontal=True,
                key="m3_heat_metric",
                format_func=lambda value: "销量" if value == "Units" else "销额",
            )
        with heat_note:
            st.caption(
                "用于识别各品牌的主要容量段。空白格代表无记录；0 代表源数据中的真实 0。"
            )
        heat = heatmap_data(data.market_long, heat_year, heat_metric)
        st.plotly_chart(
            brand_segment_heatmap(heat, heat_year, heat_metric),
            width="stretch",
            config=PLOTLY_CONFIG,
            key="chart_brand_segment_heatmap",
        )

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Module 4
# ---------------------------------------------------------------------------
section_header(
    "04",
    "Price Tracking",
    "核心竞品价格变化分析",
    "追踪 Amazon.fr 竞品的月度实际售价。展示名称由品牌、原始标题中的系列/型号和标准化容量组成；ASIN 仅用于后台匹配，不出现在图表、图例或价格表。",
)

with st.container(border=True):
    p_col_1, p_col_2, p_col_3, p_col_4 = st.columns([0.9, 3.4, 2.3, 1.3])
    with p_col_1:
        year_choice_4, years_4 = year_selection("年份", "m4_year")
    with p_col_2:
        brands_4 = st.multiselect(
            "品牌",
            options=data.price_brands,
            default=data.price_brands,
            key="m4_brands",
            placeholder="选择品牌",
        )
    with p_col_3:
        segments_4 = st.multiselect(
            "容量段",
            options=data.price_segments,
            default=data.price_segments,
            key="m4_segments",
            placeholder="选择容量段",
        )
    with p_col_4:
        st.caption(
            f"价格数据截至 {data.latest_price_month or '—'}。"
            "缺失月份保留断点，不插值。"
        )

    if not brands_4 or not segments_4:
        st.warning("请至少选择一个品牌和一个容量段。")
    else:
        price_frame = filter_prices(data, years_4, brands_4, segments_4)
        summary = price_summary(price_frame)
        if summary.empty:
            st.warning("当前筛选条件下没有有效历史价格记录。")
        else:
            summary_lookup = summary.set_index("ASIN")
            default_asins = top_price_products(
                price_frame, data.market_long, years_4, limit=8
            )
            option_asins = summary["ASIN"].tolist()
            option_labels = summary.set_index("ASIN")["product_name_short"].to_dict()
            selector_key = "m4_products_" + filter_signature(
                years_4, brands_4, segments_4
            )
            selected_asins = st.multiselect(
                "价格图展示产品",
                options=option_asins,
                default=default_asins,
                key=selector_key,
                format_func=lambda asin: option_labels.get(asin, "产品"),
                help="默认展示所选期间销售额靠前的 8 个有价格记录的产品；可搜索并增删。",
            )
            st.caption(
                "产品图默认聚焦核心竞品；下方汇总表覆盖当前筛选下的全部有效价格产品。"
            )
            chart_header(
                "产品月度价格变化",
                "每个点为一个真实月度售价。0 与空白不视为 0 欧元，折线在缺失月份断开；图例可隐藏或显示产品。",
            )
            if selected_asins:
                st.plotly_chart(
                    price_history_chart(
                        price_frame,
                        data.product_catalog,
                        years_4,
                        selected_asins,
                    ),
                    width="stretch",
                    config=PLOTLY_CONFIG,
                    key="chart_price_history",
                )
            else:
                st.info("请选择至少一个产品以查看价格折线。")

            st.write("")
            chart_header(
                "产品价格对比",
                "Average / Minimum / Maximum 基于当前筛选期间的有效价格；Latest Price 取最新有效月份，"
                "Price Change 仅在该最新月份的前一个自然月也有有效价格时计算。"
            )
            table = summary.copy()
            table["Capacity"] = table["capacity_wh"].map(
                lambda value: format_capacity(value) or "—"
            )
            table["Price Change"] = table["change_pct"] * 100
            display = pd.DataFrame(
                {
                    "Brand": table["brand"],
                    "Product Name": table["product_name_short"],
                    "Capacity": table["Capacity"],
                    "Capacity Segment": table["capacity_segment"],
                    "Average Price": table["average_price"],
                    "Minimum Price": table["minimum_price"],
                    "Maximum Price": table["maximum_price"],
                    "Latest Price": table["latest_price"],
                    "Latest Price Month": table["latest_price_month"],
                    "Previous Month Price": table["previous_price"],
                    "Price Change": table["Price Change"],
                    "Price per kWh": table["price_per_kwh"],
                }
            ).sort_values(
                ["Brand", "Product Name"], kind="stable"
            ).reset_index(drop=True)

            def change_style(value: object) -> str:
                if pd.isna(value):
                    return f"color: {NEUTRAL_COLOR}"
                if float(value) > 0:
                    return f"color: {NEGATIVE_COLOR}; font-weight: 600"
                if float(value) < 0:
                    return f"color: {POSITIVE_COLOR}; font-weight: 600"
                return f"color: {NEUTRAL_COLOR}"

            styled = (
                display.style.map(change_style, subset=["Price Change"])
                .format(
                    {
                        "Average Price": "€{:,.2f}",
                        "Minimum Price": "€{:,.2f}",
                        "Maximum Price": "€{:,.2f}",
                        "Latest Price": "€{:,.2f}",
                        "Previous Month Price": "€{:,.2f}",
                        "Price Change": "{:+.1f}%",
                        "Price per kWh": "€{:,.2f}",
                    },
                    na_rep="—",
                )
            )
            st.dataframe(
                styled,
                width="stretch",
                hide_index=True,
                height=min(620, 72 + len(display) * 35),
            )
            st.caption(
                f"当前表内 {len(display)} 个产品；平均售价、最低/最高价、最新价和每 kWh 价格均未对缺失值补零。"
            )

st.caption(
    "数据口径：Amazon.fr 实际历史明细；所有筛选条件实时重算 KPI 与图表。"
    "产品名称中的“capacity not recognized”表示原始标题和主表均无法可靠确认容量。"
)
