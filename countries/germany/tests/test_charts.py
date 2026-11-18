from __future__ import annotations

import pytest


from countries.germany.charts import (  # noqa: E402
    brand_performance_chart,
    capacity_performance_chart,
    donut_chart,
    heatmap_chart,
    price_line_chart,
    share_change_chart,
)
from countries.germany.config import (  # noqa: E402
    CAPACITY_SEGMENTS,
    DATA_PATH,
    FOCUS_BRANDS,
    OTHER_BRAND_LABEL,
)
from countries.germany.data_processing import (  # noqa: E402
    filter_prices,
    filter_sales,
    heatmap_table,
    load_dashboard_data,
    market_share_table,
    prepare_brand_chart_data,
    share_change_table,
    summarize_sales,
)


@pytest.fixture(scope="module")
def dashboard_data():
    return load_dashboard_data(DATA_PATH)


def test_brand_chart_uses_one_stacked_bar_per_month(dashboard_data):
    sales = filter_sales(
        dashboard_data.sales,
        years=[2026],
        brands=["Anker", "ECOFLOW", "Other brands"],
    )
    chart_sales, chart_brands = prepare_brand_chart_data(
        sales,
        ["Anker", "ECOFLOW", OTHER_BRAND_LABEL],
    )
    figure = brand_performance_chart(
        chart_sales,
        selected_brands=chart_brands,
        years=[2026],
        mode="Stacked bars",
    )
    assert len(figure.data) == 6
    assert sum(trace.type == "bar" for trace in figure.data) == 3
    assert sum(trace.type == "scatter" for trace in figure.data) == 3
    assert figure.layout.barmode == "stack"
    assert len(figure.layout.xaxis.tickvals) == 12


def test_ranking_chart_uses_sales_rank(dashboard_data):
    sales = filter_sales(
        dashboard_data.sales,
        years=[2026],
        brands=["Anker", "ECOFLOW"],
    )
    chart_sales, chart_brands = prepare_brand_chart_data(
        sales,
        ["Anker", "ECOFLOW"],
    )
    figure = brand_performance_chart(
        chart_sales,
        selected_brands=chart_brands,
        years=[2026],
        mode="Ranking trend",
    )
    assert all(trace.type == "scatter" for trace in figure.data)
    assert figure.layout.yaxis.title.text == "Sales rank"


def test_brand_chart_uses_single_total_revenue_line_for_all_brands(dashboard_data):
    selected = [*FOCUS_BRANDS, OTHER_BRAND_LABEL]
    sales = filter_sales(
        dashboard_data.sales,
        years=[2026],
        brands=selected,
    )
    chart_sales, chart_brands = prepare_brand_chart_data(sales, selected)
    figure = brand_performance_chart(
        chart_sales,
        selected_brands=chart_brands,
        years=[2026],
        mode="Stacked bars",
        all_brands_selected=True,
    )
    bars = [trace for trace in figure.data if trace.type == "bar"]
    lines = [trace for trace in figure.data if trace.type == "scatter"]
    assert len(bars) == 10
    assert len(lines) == 1
    assert lines[0].name == "Total Revenue"
    total_line = sum(value for value in lines[0].y if value == value)
    assert total_line == pytest.approx(sales["Revenue"].sum())


def test_capacity_chart_has_one_bar_and_one_line_per_segment(dashboard_data):
    sales = filter_sales(dashboard_data.sales, years=[2026])
    figure = capacity_performance_chart(
        sales,
        selected_segments=list(CAPACITY_SEGMENTS),
        years=[2026],
    )
    assert len(figure.data) == 10
    assert figure.layout.barmode == "stack"
    assert len(figure.layout.xaxis.tickvals) == 12


def test_donut_and_share_change_render(dashboard_data):
    categories = [*FOCUS_BRANDS, OTHER_BRAND_LABEL]
    share = market_share_table(
        dashboard_data.sales,
        2026,
        "Brand Display",
        "Units",
        categories,
    )
    units, revenue = summarize_sales(
        filter_sales(dashboard_data.sales, years=[2026])
    )
    donut = donut_chart(
        share,
        2026,
        "Brand Display",
        "Units",
        total_units=units,
        total_revenue=revenue,
    )
    assert donut.data[0].type == "pie"
    assert donut.data[0].hole == pytest.approx(0.60)

    change = share_change_table(
        dashboard_data.sales,
        "Brand Display",
        "Units",
        categories,
    )
    change_figure = share_change_chart(change, "Units")
    assert change_figure.data[0].type == "bar"


def test_heatmap_contains_all_capacity_segments(dashboard_data):
    matrix = heatmap_table(
        dashboard_data.sales,
        year=2026,
        metric="Units",
        brands=["Anker", "ECOFLOW"],
        segments=CAPACITY_SEGMENTS,
    )
    figure = heatmap_chart(matrix, metric="Units", year=2026)
    assert figure.data[0].type == "heatmap"
    assert list(figure.data[0].x) == list(CAPACITY_SEGMENTS)


def test_price_lines_keep_real_gaps(dashboard_data):
    asins = dashboard_data.price_products["ASIN"].head(3).tolist()
    prices = filter_prices(
        dashboard_data.prices,
        years=[2025],
        asins=asins,
    )
    figure = price_line_chart(
        prices,
        dashboard_data.price_products,
        selected_asins=asins,
    )
    assert len(figure.data) == len(asins)
    assert all(trace.connectgaps is False for trace in figure.data)
    assert all(trace.y is not None for trace in figure.data)
    assert all(" · " in trace.name for trace in figure.data)
    assert all("B0" not in trace.name for trace in figure.data)
    assert all("ASIN" not in trace.hovertemplate for trace in figure.data)
