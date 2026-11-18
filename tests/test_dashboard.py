from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from charts import (
    price_history_chart,
    stacked_units_revenue_chart,
)
from config import SEGMENT_COLORS, SEGMENT_ORDER
from data_processing import (
    aggregate_monthly,
    aggregate_share,
    brand_color_map,
    capacity_segment,
    filter_market,
    filter_prices,
    load_dashboard_data,
    normalize_capacity_wh,
    price_summary,
    top_price_products,
)


class DashboardDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_dashboard_data()

    def test_reference_totals(self) -> None:
        totals = self.data.market_long.groupby("year").agg(
            units=("units", lambda values: values.sum(min_count=1)),
            revenue=("revenue", lambda values: values.sum(min_count=1)),
        )
        self.assertEqual(totals.loc[2025, "units"], 10_410)
        self.assertEqual(totals.loc[2026, "units"], 7_445)
        self.assertAlmostEqual(
            totals.loc[2025, "revenue"], 12_762_391.847, places=3
        )
        self.assertAlmostEqual(
            totals.loc[2026, "revenue"], 10_198_398.4823, places=3
        )

    def test_brand_and_segment_reconcile(self) -> None:
        for year in (2025, 2026):
            frame = self.data.market_long.loc[self.data.market_long["year"] == year]
            total = frame["units"].sum(min_count=1)
            brand_total = (
                frame.groupby("brand")["units"]
                .agg(lambda values: values.sum(min_count=1))
                .sum(min_count=1)
            )
            segment_total = (
                frame.groupby("capacity_segment")["units"]
                .agg(lambda values: values.sum(min_count=1))
                .sum(min_count=1)
            )
            self.assertEqual(total, brand_total)
            self.assertEqual(total, segment_total)

            brand_share = aggregate_share(self.data.market_long, year, "Brand")
            segment_share = aggregate_share(
                self.data.market_long, year, "Capacity Segment"
            )
            self.assertAlmostEqual(brand_share["units_share"].sum(), 1.0)
            self.assertAlmostEqual(segment_share["units_share"].sum(), 1.0)

    def test_all_year_filter_combines_2025_and_2026(self) -> None:
        frame = filter_market(
            self.data, [2025, 2026], self.data.market_brands
        )
        self.assertEqual(frame["units"].sum(min_count=1), 17_855)

    def test_capacity_boundaries_are_exclusive(self) -> None:
        examples = {
            1_999: "<2kWh",
            2_000: "2–3kWh",
            2_999: "2–3kWh",
            3_000: "3–4kWh",
            3_999: "3–4kWh",
            4_000: "4–5kWh",
            5_000: "4–5kWh",
            5_001: ">5kWh",
        }
        for capacity, expected in examples.items():
            self.assertEqual(capacity_segment(capacity), expected)
        self.assertEqual(normalize_capacity_wh("1,6 kWh"), 1_600)
        self.assertEqual(normalize_capacity_wh("2 688 Wh"), 2_688)

    def test_missing_and_zero_market_records_are_distinct(self) -> None:
        self.assertTrue(self.data.market_long["units"].isna().any())
        self.assertTrue((self.data.market_long["units"] == 0).any())
        self.assertTrue(
            self.data.market_long["units"]
            .equals(self.data.market_long["units"].where(
                self.data.market_long["units_source_present"]
            ))
        )

    def test_no_duplicate_asin_month(self) -> None:
        duplicates = self.data.market_long.duplicated(
            ["ASIN", "month"], keep=False
        )
        self.assertFalse(duplicates.any())

    def test_all_brand_chart_has_one_market_revenue_line(self) -> None:
        frame = filter_market(
            self.data, [2026], self.data.market_brands
        )
        monthly = aggregate_monthly(frame, "brand", [2026])
        colors = brand_color_map(self.data.market_brands)
        figure = stacked_units_revenue_chart(
            monthly,
            self.data.market_brands,
            colors,
            [2026],
            "品牌",
            line_mode="market_total",
        )
        bar_traces = [trace for trace in figure.data if trace.type == "bar"]
        line_traces = [trace for trace in figure.data if trace.type == "scatter"]
        self.assertEqual(len(bar_traces), len(self.data.market_brands))
        self.assertEqual(len(line_traces), 1)
        self.assertEqual(line_traces[0].name, "市场总销额")

    def test_partial_brand_chart_has_brand_revenue_lines(self) -> None:
        selected = self.data.market_brands[:3]
        frame = filter_market(self.data, [2026], selected)
        monthly = aggregate_monthly(frame, "brand", [2026])
        colors = brand_color_map(self.data.market_brands)
        figure = stacked_units_revenue_chart(
            monthly,
            selected,
            colors,
            [2026],
            "品牌",
            line_mode="per_category",
        )
        line_traces = [trace for trace in figure.data if trace.type == "scatter"]
        self.assertEqual(len(line_traces), len(selected))

    def test_capacity_chart_uses_fixed_segment_colors(self) -> None:
        frame = filter_market(
            self.data, [2026], self.data.market_brands
        )
        monthly = aggregate_monthly(frame, "capacity_segment", [2026])
        figure = stacked_units_revenue_chart(
            monthly,
            SEGMENT_ORDER,
            SEGMENT_COLORS,
            [2026],
            "容量段",
            line_mode="per_category",
        )
        bar_traces = {
            trace.name: trace.marker.color
            for trace in figure.data
            if trace.type == "bar"
        }
        for segment in SEGMENT_ORDER:
            self.assertEqual(bar_traces[segment], SEGMENT_COLORS[segment])

    def test_price_zero_is_missing_and_change_formula_is_exact(self) -> None:
        price_frame = filter_prices(
            self.data,
            [2025, 2026],
            self.data.price_brands,
            self.data.price_segments,
        )
        self.assertFalse((price_frame["price"] == 0).any())
        self.assertTrue(price_frame["price"].isna().any())

        summary = price_summary(price_frame)
        for row in summary.loc[summary["change_pct"].notna()].itertuples():
            expected = (
                (row.latest_price - row.previous_price) / row.previous_price
            )
            self.assertAlmostEqual(row.change_pct, expected, places=12)

    def test_product_display_names_do_not_contain_asin(self) -> None:
        self.assertFalse(
            self.data.product_catalog["product_name_short"]
            .str.contains(r"\bB0[A-Z0-9]{8}\b", regex=True)
            .any()
        )

    def test_price_chart_trace_names_do_not_contain_asin(self) -> None:
        price_frame = filter_prices(
            self.data,
            [2026],
            self.data.price_brands,
            self.data.price_segments,
        )
        asins = top_price_products(
            price_frame, self.data.market_long, [2026], 8
        )
        figure = price_history_chart(
            price_frame, self.data.product_catalog, [2026], asins
        )
        self.assertFalse(
            any("B0" in trace.name for trace in figure.data)
        )

    def test_source_validation_has_full_overlap(self) -> None:
        joined = " ".join(self.data.validation_notes)
        self.assertIn("92 个聚合页/月份", joined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
