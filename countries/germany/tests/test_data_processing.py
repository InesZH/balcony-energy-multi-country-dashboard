from __future__ import annotations

import pandas as pd
import pytest


from countries.germany.config import (  # noqa: E402
    CAPACITY_SEGMENTS,
    DATA_PATH,
    FOCUS_BRANDS,
    OTHER_BRAND_LABEL,
)
from countries.germany.data_processing import (  # noqa: E402
    assign_capacity_segment,
    build_price_summary,
    filter_prices,
    filter_sales,
    load_dashboard_data,
    market_share_table,
    prepare_brand_chart_data,
    summarize_sales,
)


@pytest.fixture(scope="module")
def dashboard_data():
    return load_dashboard_data(DATA_PATH)


def test_source_is_loaded_with_expected_coverage(dashboard_data):
    assert dashboard_data.quality.asin_count == 89
    assert dashboard_data.quality.brand_count == 27
    assert dashboard_data.quality.focus_brand_count == 12
    assert len(dashboard_data.quality.months) == 22
    assert dashboard_data.quality.latest_month == pd.Timestamp("2026-10-01")
    assert dashboard_data.quality.price_products_found == 11
    assert dashboard_data.quality.duplicate_asin_months == 0


def test_capacity_sheet_reconciles_to_asin_detail(dashboard_data):
    assert dashboard_data.quality.capacity_reconciles
    assert dashboard_data.quality.capacity_max_diff == 0
    assert dashboard_data.quality.capacity_mismatch_months == 0


@pytest.mark.parametrize(
    ("capacity", "expected"),
    [
        (1599, "<2kWh"),
        (2000, "2-3kWh"),
        (2999, "2-3kWh"),
        (3000, "3-4kWh"),
        (4000, "4-5kWh"),
        (5000, "4-5kWh"),
        (5001, ">5kWh"),
    ],
)
def test_capacity_boundaries_are_mutually_exclusive(capacity, expected):
    assert assign_capacity_segment(capacity) == expected


@pytest.mark.parametrize("metric", ["Units", "Revenue"])
@pytest.mark.parametrize(
    ("dimension", "categories"),
    [
        ("Capacity Segment", CAPACITY_SEGMENTS),
        ("Brand Display", [*FOCUS_BRANDS, OTHER_BRAND_LABEL]),
    ],
)
@pytest.mark.parametrize("year", [2025, 2026])
def test_market_share_sums_to_100(
    dashboard_data,
    metric,
    dimension,
    categories,
    year,
):
    table = market_share_table(
        dashboard_data.sales,
        year=year,
        dimension=dimension,
        metric=metric,
        categories=categories,
    )
    assert table["Share"].sum(min_count=1) == pytest.approx(100.0, abs=1e-9)


def test_year_filter_updates_totals(dashboard_data):
    sales_2025 = filter_sales(dashboard_data.sales, years=[2025])
    sales_2026 = filter_sales(dashboard_data.sales, years=[2026])
    units_2025, revenue_2025 = summarize_sales(sales_2025)
    units_2026, revenue_2026 = summarize_sales(sales_2026)
    assert units_2025 is not None and units_2026 is not None
    assert revenue_2025 is not None and revenue_2026 is not None
    assert units_2025 > 0
    assert units_2026 > 0
    assert units_2025 != units_2026
    assert revenue_2025 != revenue_2026


def test_brand_filter_returns_only_selected_brands(dashboard_data):
    filtered = filter_sales(
        dashboard_data.sales,
        years=[2026],
        brands=["Anker", "ECOFLOW"],
    )
    assert set(filtered["Brand Display"].unique()) == {"Anker", "ECOFLOW"}


def test_real_zeros_are_retained_but_prices_are_not_faked(dashboard_data):
    target_price = dashboard_data.prices[
        dashboard_data.prices["ASIN"].isin(
            dashboard_data.price_products["ASIN"]
        )
    ]
    assert target_price["Price"].dropna().gt(0).all()
    assert target_price["Price"].isna().any()
    assert not target_price["Price"].eq(0).any()
    assert dashboard_data.quality.price_zero_records > 0


def test_price_summary_uses_latest_calendar_month(dashboard_data):
    selected = list(dashboard_data.price_products["ASIN"].head(4))
    price_2026 = filter_prices(
        dashboard_data.prices,
        years=[2026],
        asins=selected,
    )
    summary = build_price_summary(
        price_2026,
        dashboard_data.price_products,
        selected_asins=selected,
    )
    assert len(summary) == len(selected)
    assert summary["Latest Month"].notna().all()
    assert summary["Latest Price"].notna().all()
    expected_change = (
        summary["Latest Price"] - summary["Previous Month Price"]
    ) / summary["Previous Month Price"] * 100
    pd.testing.assert_series_equal(
        summary["Price Change (%)"],
        expected_change,
        check_names=False,
        rtol=1e-10,
        atol=1e-10,
    )


def test_price_products_have_distinct_brand_series_capacity_labels(dashboard_data):
    catalog = dashboard_data.price_products
    assert catalog["Product Label"].is_unique
    assert catalog["Product Label"].str.contains("Wh").all()
    assert not catalog["Product Label"].str.contains("B0").any()
    assert {
        "SOLIX 3 Pro + Panels",
        "SOLIX 3 Pro + BP2700",
        "STREAM AC Pro",
        "B2500",
    }.issubset(set(catalog["Series"]))


def test_capacity_segment_missing_is_not_coerced_to_zero(dashboard_data):
    missing_capacity = dashboard_data.sales["Capacity Segment"].isna()
    missing_units = dashboard_data.sales.loc[missing_capacity, "Units"]
    assert missing_units.isna().all() or missing_capacity.sum() == 0
    assert not dashboard_data.sales["Capacity Segment"].eq("0").any()


def test_brand_display_groups_non_focus_brands(dashboard_data):
    non_focus = dashboard_data.sales[~dashboard_data.sales["Brand"].isin(FOCUS_BRANDS)]
    assert not non_focus.empty
    assert set(non_focus["Brand Display"].unique()) == {OTHER_BRAND_LABEL}


def test_brand_chart_reduces_three_secondary_brands_without_changing_totals(dashboard_data):
    selected = [*FOCUS_BRANDS, OTHER_BRAND_LABEL]
    filtered = filter_sales(dashboard_data.sales, years=[2026], brands=selected)
    chart_sales, categories = prepare_brand_chart_data(filtered, selected)
    assert not {"TSUN", "Mentech", "Jackery"}.intersection(categories)
    assert len(categories) == 10
    assert chart_sales["Units"].sum() == pytest.approx(filtered["Units"].sum())
    grouped_other = (
        chart_sales.loc[chart_sales["Chart Brand"] == OTHER_BRAND_LABEL, "Units"].sum()
    )
    original_other = (
        filtered.loc[filtered["Brand Display"] == OTHER_BRAND_LABEL, "Units"].sum()
    )
    assert grouped_other > original_other


def test_missing_month_values_remain_nan(dashboard_data):
    future = dashboard_data.sales[dashboard_data.sales["Date"].dt.month.isin([11, 12]) & (dashboard_data.sales["Year"] == 2026)]
    assert future.empty

