from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import (
    NEGATIVE_COLOR,
    NEUTRAL_COLOR,
    POSITIVE_COLOR,
    SEGMENT_COLORS,
    SEGMENT_ORDER,
)
from data_processing import (
    format_capacity,
    format_period,
    period_to_date,
    selected_periods,
)


FONT_FAMILY = 'Inter, "Segoe UI", Arial, sans-serif'
GRID_COLOR = "#E8ECEF"
TEXT_COLOR = "#27343D"
MUTED_COLOR = "#5F6D76"
PLOT_BACKGROUND = "#FFFFFF"


def _base_layout(height: int, margin_bottom: int = 60) -> dict:
    return {
        "height": height,
        "margin": {"l": 66, "r": 74, "t": 86, "b": margin_bottom},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": PLOT_BACKGROUND,
        "font": {"family": FONT_FAMILY, "color": TEXT_COLOR, "size": 12},
        "hoverlabel": {
            "bgcolor": "#FFFFFF",
            "bordercolor": "#D9E0E4",
            "font": {"family": FONT_FAMILY, "color": TEXT_COLOR, "size": 12},
        },
    }


def _period_tick_text(periods: list[str]) -> list[str]:
    years = {period[:4] for period in periods}
    return [
        format_period(period, include_year=len(years) > 1)
        for period in periods
    ]


def _safe_number(value: object, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):,.{decimals}f}"


def stacked_units_revenue_chart(
    monthly_category: pd.DataFrame,
    category_order: Iterable[str],
    colors: dict[str, str],
    years: Iterable[int],
    category_label: str,
    line_mode: str = "per_category",
    market_line_color: str = "#415363",
) -> go.Figure:
    years = list(years)
    periods = selected_periods(years)
    categories = [category for category in category_order if category in set(
        monthly_category["category"].dropna().astype(str).unique()
    )]
    tick_text = _period_tick_text(periods)
    tick_map = dict(zip(periods, tick_text, strict=False))

    figure = make_subplots(specs=[[{"secondary_y": True}]])
    units_pivot = (
        monthly_category.pivot(index="month", columns="category", values="units")
        .reindex(index=periods, columns=categories)
    )
    revenue_pivot = (
        monthly_category.pivot(index="month", columns="category", values="revenue")
        .reindex(index=periods, columns=categories)
    )
    totals = (
        monthly_category.groupby("month", dropna=False)
        .agg(
            units=("units", lambda values: values.sum(min_count=1)),
            revenue=("revenue", lambda values: values.sum(min_count=1)),
        )
        .reindex(periods)
    )

    for category in categories:
        total_units = totals["units"].tolist()
        total_revenue = totals["revenue"].tolist()
        customdata = list(zip(total_units, total_revenue, strict=False))
        figure.add_trace(
            go.Bar(
                x=periods,
                y=units_pivot[category].tolist(),
                name=category,
                marker={"color": colors.get(category, "#8796A2"), "line": {"width": 0}},
                legendgroup=f"{category_label}:{category}",
                customdata=customdata,
                hovertemplate=(
                    f"<b>{category}</b><br>"
                    f"{category_label}: %{{fullData.name}}<br>"
                    "月份: %{x}<br>"
                    "销量: %{y:,.0f} Units<br>"
                    "当月总销量: %{customdata[0]:,.0f} Units<br>"
                    "当月销售额: €%{customdata[1]:,.2f}"
                    "<extra></extra>"
                ),
            ),
            secondary_y=False,
        )

    if line_mode == "market_total":
        figure.add_trace(
            go.Scatter(
                x=periods,
                y=totals["revenue"].tolist(),
                mode="lines+markers",
                name="市场总销额",
                line={"color": market_line_color, "width": 2.6},
                marker={"size": 6, "color": market_line_color},
                connectgaps=False,
                hovertemplate=(
                    "<b>市场总销额</b><br>"
                    "月份: %{x}<br>"
                    "销售额: €%{y:,.2f}<br>"
                    "市场总销量: %{customdata[0]:,.0f} Units"
                    "<extra></extra>"
                ),
                customdata=[[value] for value in totals["units"].tolist()],
            ),
            secondary_y=True,
        )
    else:
        for category in categories:
            figure.add_trace(
                go.Scatter(
                    x=periods,
                    y=revenue_pivot[category].tolist(),
                    mode="lines+markers",
                    name=category,
                    legendgroup=f"{category_label}:{category}",
                    showlegend=False,
                    line={"color": colors.get(category, "#8796A2"), "width": 2.4},
                    marker={"size": 5},
                    connectgaps=False,
                    customdata=[
                        [category, value]
                        for value in units_pivot[category].tolist()
                    ],
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        f"{category_label}: %{{customdata[0]}}<br>"
                        "月份: %{x}<br>"
                        "销售额: €%{y:,.2f}<br>"
                        "销量: %{customdata[1]:,.0f} Units"
                        "<extra></extra>"
                    ),
                ),
                secondary_y=True,
            )

    layout = _base_layout(510, margin_bottom=70)
    layout.update(
        {
            "barmode": "stack",
            "bargap": 0.28,
            "hovermode": "x unified" if line_mode == "market_total" else "closest",
            "legend": {
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "left",
                "x": 0,
                "font": {"size": 11},
                "itemclick": "toggle",
                "itemdoubleclick": "toggleothers",
            },
            "xaxis": {
                "type": "category",
                "tickmode": "array",
                "tickvals": periods,
                "ticktext": [tick_map[period] for period in periods],
                "tickangle": -35,
                "gridcolor": GRID_COLOR,
                "zeroline": False,
                "showline": False,
                "fixedrange": False,
            },
            "yaxis": {
                "title": {"text": "销量（Units）", "standoff": 12},
                "tickformat": ",.0f",
                "rangemode": "tozero",
                "gridcolor": GRID_COLOR,
                "zeroline": False,
                "fixedrange": False,
            },
            "yaxis2": {
                "title": {"text": "销售额（€）", "standoff": 12},
                "tickprefix": "€",
                "tickformat": ".3s",
                "rangemode": "tozero",
                "showgrid": False,
                "zeroline": False,
                "fixedrange": False,
            },
        }
    )
    figure.update_layout(**layout)
    return figure


def market_share_donut(
    share_frame: pd.DataFrame,
    year: int,
    dimension: str,
    metric: str,
    colors: dict[str, str],
) -> go.Figure:
    dimension_column = "brand" if dimension == "Brand" else "capacity_segment"
    metric_column = "units_share" if metric == "Units Share" else "revenue_share"
    frame = share_frame.loc[
        share_frame[metric_column].notna()
        & (share_frame[metric_column] > 0)
    ].copy()
    labels = frame[dimension_column].astype(str)
    values = frame[metric_column]
    total_units = share_frame.attrs.get("total_units", np.nan)
    total_revenue = share_frame.attrs.get("total_revenue", np.nan)
    center_value = (
        f"{_safe_number(total_units)}<br><span style='font-size:12px;color:{MUTED_COLOR}'>Units</span>"
        if metric == "Units Share"
        else f"€{_safe_number(total_revenue)}<br><span style='font-size:12px;color:{MUTED_COLOR}'>Revenue</span>"
    )

    customdata = list(
        zip(
            frame["units"].tolist(),
            frame["revenue"].tolist(),
            frame[metric_column].tolist(),
            strict=False,
        )
    )
    figure = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.64,
            sort=False,
            direction="clockwise",
            marker={
                "colors": [colors.get(label, "#8B99A4") for label in labels],
                "line": {"color": "#FFFFFF", "width": 2},
            },
            textinfo="none",
            customdata=customdata,
            hovertemplate=(
                f"<b>%{{label}}</b><br>{year}<br>"
                "销量: %{customdata[0]:,.0f} Units<br>"
                "销售额: €%{customdata[1]:,.2f}<br>"
                "市场份额: %{customdata[2]:.1%}"
                "<extra></extra>"
            ),
        )
    )
    figure.add_annotation(
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        text=center_value,
        showarrow=False,
        align="center",
        font={"family": FONT_FAMILY, "size": 19, "color": TEXT_COLOR},
    )
    figure.update_layout(
        height=390,
        margin={"l": 10, "r": 10, "t": 14, "b": 98},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=PLOT_BACKGROUND,
        font={"family": FONT_FAMILY, "color": TEXT_COLOR, "size": 11},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.19,
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 10},
        },
        hoverlabel={
            "bgcolor": "#FFFFFF",
            "bordercolor": "#D9E0E4",
            "font": {"family": FONT_FAMILY, "color": TEXT_COLOR},
        },
        showlegend=True,
    )
    return figure


def share_change_chart(
    change_frame: pd.DataFrame,
    dimension: str,
    metric: str,
) -> go.Figure:
    dimension_column = "brand" if dimension == "Brand" else "capacity_segment"
    frame = change_frame.sort_values("change_pp", ascending=True).copy()
    bar_colors = []
    for value in frame["change_pp"]:
        if abs(value) < 0.05:
            bar_colors.append(NEUTRAL_COLOR)
        elif value > 0:
            bar_colors.append(POSITIVE_COLOR)
        else:
            bar_colors.append(NEGATIVE_COLOR)

    figure = go.Figure(
        go.Bar(
            x=frame["change_pp"],
            y=frame[dimension_column],
            orientation="h",
            marker={"color": bar_colors, "line": {"width": 0}},
            text=[f"{value:+.1f} pp" for value in frame["change_pp"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                f"<b>%{{y}}</b><br>{metric}<br>"
                "2026 − 2025: %{x:+.2f} pp<extra></extra>"
            ),
        )
    )
    dynamic_height = max(310, 54 + len(frame) * 35)
    figure.update_layout(
        **_base_layout(dynamic_height, margin_bottom=58),
        xaxis={
            "title": {"text": "份额变化（百分点，pp）", "standoff": 12},
            "ticksuffix": " pp",
            "zeroline": True,
            "zerolinecolor": "#7F8A93",
            "zerolinewidth": 1,
            "gridcolor": GRID_COLOR,
            "fixedrange": False,
        },
        yaxis={
            "title": "",
            "automargin": True,
            "gridcolor": GRID_COLOR,
            "fixedrange": False,
        },
        showlegend=False,
    )
    return figure


def brand_segment_heatmap(
    heatmap: pd.DataFrame,
    year: int,
    metric: str,
) -> go.Figure:
    metric_column = "units" if metric == "Units" else "revenue"
    full = heatmap.copy()
    row_totals = full.sum(axis=1, min_count=1)
    full = full.loc[row_totals.sort_values(ascending=True).index]

    share = full.div(full.sum(axis=0, min_count=1), axis=1)
    customdata = np.empty((*full.shape, 3), dtype=object)
    for row_index, brand in enumerate(full.index):
        for column_index, segment in enumerate(full.columns):
            value = full.iloc[row_index, column_index]
            if pd.isna(value):
                value_text = "无记录"
            elif metric_column == "units":
                value_text = f"{value:,.0f} Units"
            else:
                value_text = f"€{value:,.2f}"
            share_value = share.iloc[row_index, column_index]
            share_text = (
                f"{share_value:.1%}" if pd.notna(share_value) else "无记录"
            )
            customdata[row_index, column_index, 0] = value_text
            customdata[row_index, column_index, 1] = share_text
            customdata[row_index, column_index, 2] = (
                f"{year} · "
                + ("Units" if metric_column == "units" else "Revenue")
            )

    figure = go.Figure(
        go.Heatmap(
            z=full.values,
            x=full.columns,
            y=full.index,
            colorscale=[
                [0.0, "#F2F6F7"],
                [0.35, "#C5DCDD"],
                [0.70, "#78A8AC"],
                [1.0, "#326C74"],
            ],
            zmin=0,
            hovertemplate=(
                "<b>%{y}</b><br>%{x}<br>"
                + ("销量: " if metric_column == "units" else "销售额: ")
                + "%{customdata[0]}<br>容量段内份额: %{customdata[1]}<br>%{customdata[2]}"
                "<extra></extra>"
            ),
            customdata=customdata,
            colorbar={
                "title": "Units" if metric_column == "units" else "Revenue (€)",
                "len": 0.72,
                "thickness": 10,
                "outlinewidth": 0,
                "tickfont": {"size": 10},
            },
            xgap=3,
            ygap=3,
        )
    )
    figure.update_layout(
        height=max(390, 110 + len(full.index) * 42),
        margin={"l": 102, "r": 66, "t": 34, "b": 56},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=PLOT_BACKGROUND,
        font={"family": FONT_FAMILY, "color": TEXT_COLOR, "size": 11},
        xaxis={
            "title": "",
            "side": "bottom",
            "tickangle": 0,
            "fixedrange": False,
        },
        yaxis={"title": "", "automargin": True, "fixedrange": False},
        hoverlabel={
            "bgcolor": "#FFFFFF",
            "bordercolor": "#D9E0E4",
            "font": {"family": FONT_FAMILY, "color": TEXT_COLOR},
        },
    )
    return figure


def price_history_chart(
    price_frame: pd.DataFrame,
    catalog: pd.DataFrame,
    years: Iterable[int],
    selected_asins: Iterable[str],
) -> go.Figure:
    years = list(years)
    periods = selected_periods(years)
    tick_map = dict(zip(periods, _period_tick_text(periods), strict=False))
    selected_asins = list(selected_asins)
    frame = price_frame.loc[
        price_frame["ASIN"].isin(selected_asins) & price_frame["price"].notna()
    ].copy()
    meta = catalog.set_index("ASIN")
    figure = go.Figure()

    for asin in selected_asins:
        product_prices = frame.loc[frame["ASIN"] == asin].sort_values("date")
        if asin not in meta.index:
            continue
        product = meta.loc[asin]
        prices = product_prices.set_index("month")["price"].reindex(periods)
        color = product["product_color"]
        figure.add_trace(
            go.Scatter(
                x=periods,
                y=prices.tolist(),
                mode="lines+markers",
                name=product["product_name_short"],
                line={"color": color, "width": 2.3},
                marker={"size": 5, "color": color},
                connectgaps=False,
                customdata=[
                    [
                        product["brand"],
                        product["series"],
                        format_capacity(product["capacity_wh"]) or "未识别",
                    ]
                    for _ in periods
                ],
                hovertemplate=(
                    f"<b>{product['product_name_short']}</b><br>"
                    "品牌: %{customdata[0]}<br>"
                    "产品系列: %{customdata[1]}<br>"
                    "容量: %{customdata[2]}<br>"
                    "月份: %{x}<br>"
                    "售价: €%{y:,.2f}"
                    "<extra></extra>"
                ),
            )
        )

    layout = _base_layout(600, margin_bottom=176)
    layout.update(
        {
            "legend": {
                "orientation": "h",
                "yanchor": "top",
                "y": -0.20,
                "xanchor": "left",
                "x": 0,
                "font": {"size": 10},
                "itemclick": "toggle",
                "itemdoubleclick": "toggleothers",
            },
            "xaxis": {
                "type": "category",
                "tickmode": "array",
                "tickvals": periods,
                "ticktext": [tick_map[period] for period in periods],
                "tickangle": 0 if len(periods) <= 12 else -42,
                "gridcolor": GRID_COLOR,
                "fixedrange": False,
            },
            "yaxis": {
                "title": {"text": "产品售价（€）", "standoff": 12},
                "tickprefix": "€",
                "tickformat": ",.0f",
                "rangemode": "tozero",
                "gridcolor": GRID_COLOR,
                "fixedrange": False,
            },
            "hovermode": "closest",
        }
    )
    figure.update_layout(**layout)
    return figure
