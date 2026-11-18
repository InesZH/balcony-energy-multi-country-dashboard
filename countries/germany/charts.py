from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import (
    BRAND_COLORS,
    CAPACITY_COLORS,
    CAPACITY_SEGMENTS,
    GRID,
    INK,
    MUTED,
    PRICE_CHANGE_GREEN,
    PRICE_CHANGE_GREY,
    PRICE_CHANGE_RED,
    SHARE_DOWN_RED,
    SHARE_FLAT_GREY,
    SHARE_UP_GREEN,
)
from .data_processing import active_months, month_label


FONT_FAMILY = "Segoe UI, Inter, Arial, sans-serif"


def _apply_theme(
    figure: go.Figure,
    title: str,
    height: int = 520,
    showlegend: bool = True,
) -> go.Figure:
    figure.update_layout(
        title={
            "text": title,
            "x": 0.01,
            "y": 0.98,
            "xanchor": "left",
            "font": {"size": 17, "color": INK, "family": FONT_FAMILY},
        },
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        font={"family": FONT_FAMILY, "size": 12, "color": INK},
        hovermode="closest",
        hoverlabel={
            "bgcolor": "#FFFFFF",
            "bordercolor": "#D6DEE9",
            "font": {"family": FONT_FAMILY, "size": 12, "color": INK},
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.10,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 10, "family": FONT_FAMILY},
            "itemclick": "toggle",
            "itemdoubleclick": "toggleothers",
        },
        showlegend=showlegend,
        margin={"l": 54, "r": 58, "t": 132, "b": 46},
        bargap=0.18,
        bargroupgap=0.04,
    )
    figure.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor="#CDD5E0",
        tickfont={"family": FONT_FAMILY, "size": 11, "color": MUTED},
        title_font={"family": FONT_FAMILY, "size": 12, "color": MUTED},
    )
    figure.update_yaxes(
        gridcolor=GRID,
        zerolinecolor="#CDD5E0",
        tickfont={"family": FONT_FAMILY, "size": 11, "color": MUTED},
        title_font={"family": FONT_FAMILY, "size": 12, "color": MUTED},
    )
    return figure


def _month_axis(
    dates: Iterable[pd.Timestamp],
    include_year: bool,
) -> tuple[list[pd.Timestamp], list[str]]:
    values = [pd.Timestamp(date) for date in dates]
    labels = [month_label(date, include_year=include_year) for date in values]
    return values, labels


def brand_performance_chart(
    sales: pd.DataFrame,
    selected_brands: list[str],
    years: list[int],
    mode: str,
    all_brands_selected: bool = False,
) -> go.Figure:
    dates = active_months(years)
    include_year = len(years) > 1
    x_values, x_labels = _month_axis(dates, include_year)

    units = (
        sales.groupby(["Date", "Chart Brand"])["Units"]
        .sum(min_count=1)
        .unstack("Chart Brand")
        .reindex(index=dates, columns=selected_brands)
    )
    revenue = (
        sales.groupby(["Date", "Chart Brand"])["Revenue"]
        .sum(min_count=1)
        .unstack("Chart Brand")
        .reindex(index=dates, columns=selected_brands)
    )

    is_rank = mode == "Ranking trend"
    figure = make_subplots(
        specs=[[{"secondary_y": not is_rank}]],
        horizontal_spacing=0.02,
    )

    if is_rank:
        ranks = units.rank(
            axis=1,
            method="min",
            ascending=False,
            na_option="keep",
        )
        for brand in selected_brands:
            figure.add_trace(
                go.Scatter(
                    x=x_values,
                    y=ranks[brand].to_numpy(),
                    mode="lines+markers",
                    name=brand,
                    legendgroup=brand,
                    line={"width": 2.2, "color": BRAND_COLORS.get(brand, "#8B97A6")},
                    marker={"size": 6},
                    connectgaps=False,
                    hovertemplate=(
                        f"<b>{brand}</b><br>%{{x|%b %Y}}"
                        "<br>Sales rank: %{y:.0f}<extra></extra>"
                    ),
                )
            )
        title = "品牌月度销量排名变化 · 排名 1 为最高"
    else:
        for brand in selected_brands:
            color = BRAND_COLORS.get(brand, "#8B97A6")
            figure.add_trace(
                go.Bar(
                    x=x_values,
                    y=units[brand].to_numpy(),
                    name=brand,
                    legendgroup=brand,
                    marker={"color": color, "line": {"width": 0}},
                    opacity=0.88,
                    hovertemplate=(
                        f"<b>{brand}</b><br>%{{x|%b %Y}}"
                        "<br>Units: %{y:,.0f}<extra></extra>"
                    ),
                ),
                secondary_y=False,
            )
        if all_brands_selected:
            total_revenue = (
                revenue.sum(axis=1, min_count=1)
                if not revenue.empty
                else pd.Series(dtype=float)
            )
            figure.add_trace(
                go.Scatter(
                    x=x_values,
                    y=total_revenue.to_numpy(),
                    name="Total Revenue",
                    legendgroup="Total Revenue",
                    mode="lines+markers",
                    line={"width": 2.8, "color": "#0B2447"},
                    marker={
                        "size": 6,
                        "color": "#FFFFFF",
                        "line": {"width": 1.5, "color": "#0B2447"},
                    },
                    connectgaps=False,
                    hovertemplate=(
                        "所有品牌合计<br>%{x|%b %Y}"
                        "<br>Total Revenue: €%{y:,.0f}<extra></extra>"
                    ),
                ),
                secondary_y=True,
            )
        else:
            for brand in selected_brands:
                color = BRAND_COLORS.get(brand, "#8B97A6")
                figure.add_trace(
                    go.Scatter(
                        x=x_values,
                        y=revenue[brand].to_numpy(),
                        name=brand,
                        legendgroup=brand,
                        showlegend=False,
                        mode="lines+markers",
                        line={"width": 1.8, "color": color},
                        marker={
                            "size": 4,
                            "color": "#FFFFFF",
                            "line": {"width": 1.2, "color": color},
                        },
                        connectgaps=False,
                        hovertemplate=(
                            f"<b>{brand}</b><br>%{{x|%b %Y}}"
                            "<br>Revenue: €%{y:,.0f}<extra></extra>"
                        ),
                    ),
                    secondary_y=True,
                )
        title = "品牌月度销量与销额 · 每月一根堆叠柱"

    figure.update_layout(barmode="stack")
    figure.update_xaxes(
        tickmode="array",
        tickvals=x_values,
        ticktext=x_labels,
        tickangle=-35,
        automargin=True,
    )
    if is_rank:
        brand_total = units.sum(min_count=1).sort_values(ascending=False)
        rank_max = max(int(len(brand_total)), 1)
        figure.update_yaxes(
            title="Sales rank",
            autorange="reversed",
            tickmode="linear",
            tick0=1,
            dtick=1,
            range=[rank_max + 0.5, 0.5],
        )
    else:
        figure.update_yaxes(
            title="Units (units)",
            rangemode="tozero",
            tickformat=",.0f",
            secondary_y=False,
        )
        figure.update_yaxes(
            title="Revenue (€)",
            rangemode="tozero",
            tickprefix="€",
            tickformat="~s",
            showgrid=False,
            secondary_y=True,
        )
    return _apply_theme(figure, title=title, height=560)


def capacity_performance_chart(
    sales: pd.DataFrame,
    selected_segments: list[str],
    years: list[int],
) -> go.Figure:
    dates = active_months(years)
    include_year = len(years) > 1
    x_values, x_labels = _month_axis(dates, include_year)

    units = (
        sales.groupby(["Date", "Capacity Segment"])["Units"]
        .sum(min_count=1)
        .unstack("Capacity Segment")
        .reindex(index=dates, columns=selected_segments)
    )
    revenue = (
        sales.groupby(["Date", "Capacity Segment"])["Revenue"]
        .sum(min_count=1)
        .unstack("Capacity Segment")
        .reindex(index=dates, columns=selected_segments)
    )

    figure = make_subplots(specs=[[{"secondary_y": True}]])
    for segment in selected_segments:
        color = CAPACITY_COLORS[segment]
        figure.add_trace(
            go.Bar(
                x=x_values,
                y=units[segment].to_numpy(),
                name=segment,
                legendgroup=segment,
                marker={"color": color},
                opacity=0.9,
                hovertemplate=(
                    f"<b>{segment}</b><br>%{{x|%b %Y}}"
                    "<br>Units: %{y:,.0f}<extra></extra>"
                ),
            ),
            secondary_y=False,
        )
        figure.add_trace(
            go.Scatter(
                x=x_values,
                y=revenue[segment].to_numpy(),
                name=segment,
                legendgroup=segment,
                showlegend=False,
                mode="lines+markers",
                line={"width": 2, "color": color},
                marker={
                    "size": 5,
                    "color": "#FFFFFF",
                    "line": {"width": 1.2, "color": color},
                },
                connectgaps=False,
                hovertemplate=(
                    f"<b>{segment}</b><br>%{{x|%b %Y}}"
                    "<br>Revenue: €%{y:,.0f}<extra></extra>"
                ),
            ),
            secondary_y=True,
        )

    figure.update_layout(barmode="stack")
    figure.update_xaxes(
        tickmode="array",
        tickvals=x_values,
        ticktext=x_labels,
        tickangle=-35,
        automargin=True,
    )
    figure.update_yaxes(
        title="Units (units)",
        rangemode="tozero",
        tickformat=",.0f",
        secondary_y=False,
    )
    figure.update_yaxes(
        title="Revenue (€)",
        rangemode="tozero",
        tickprefix="€",
        tickformat="~s",
        showgrid=False,
        secondary_y=True,
    )
    return _apply_theme(
        figure,
        "容量段月度销量与销额 · 每月一根堆叠柱",
        height=540,
    )


def donut_chart(
    share_table: pd.DataFrame,
    year: int,
    dimension: str,
    metric: str,
    total_units: float | None,
    total_revenue: float | None,
) -> go.Figure:
    data = share_table.dropna(subset=["Share"]).copy()
    data = data[data["Share"] > 0]
    color_map = BRAND_COLORS if dimension == "Brand Display" else CAPACITY_COLORS
    colors = [color_map.get(category, "#8B97A6") for category in data["Category"]]

    center_value = (
        f"{total_units:,.0f} units"
        if metric == "Units" and total_units is not None
        else f"€{total_revenue:,.0f}" if total_revenue is not None else "—"
    )

    figure = go.Figure(
        go.Pie(
            labels=data["Category"],
            values=data["Share"],
            hole=0.60,
            sort=False,
            direction="clockwise",
            rotation=-12,
            marker={"colors": colors, "line": {"color": "#FFFFFF", "width": 2}},
            textinfo="percent",
            textposition="inside",
            insidetextorientation="radial",
            hovertemplate=(
                "<b>%{label}</b>"
                "<br>Units: %{customdata[0]:,.0f}"
                "<br>Revenue: €%{customdata[1]:,.0f}"
                "<br>Share: %{percent}"
                "<extra></extra>"
            ),
            customdata=np.stack(
                [
                    pd.to_numeric(data["Units"], errors="coerce").fillna(0),
                    pd.to_numeric(data["Revenue"], errors="coerce").fillna(0),
                ],
                axis=-1,
            ),
        )
    )
    figure.add_annotation(
        x=0.5,
        y=0.54,
        text=str(year),
        showarrow=False,
        font={"size": 13, "color": MUTED, "family": FONT_FAMILY},
    )
    figure.add_annotation(
        x=0.5,
        y=0.46,
        text=center_value,
        showarrow=False,
        font={"size": 17, "color": INK, "family": FONT_FAMILY},
    )
    return _apply_theme(
        figure,
        f"{year} 年{'销量' if metric == 'Units' else '销额'}份额",
        height=480,
    )


def share_change_chart(
    comparison: pd.DataFrame,
    metric: str,
) -> go.Figure:
    data = comparison.dropna(subset=["Change pp"]).copy()
    data = data.sort_values("Change pp", ascending=True)
    colors = [
        SHARE_UP_GREEN
        if value > 0.05
        else SHARE_DOWN_RED if value < -0.05 else SHARE_FLAT_GREY
        for value in data["Change pp"]
    ]
    figure = go.Figure(
        go.Bar(
            x=data["Change pp"],
            y=data["Category"],
            orientation="h",
            marker={"color": colors},
            customdata=np.stack(
                [
                    data["2025 Share"].fillna(np.nan),
                    data["2026 Share"].fillna(np.nan),
                ],
                axis=-1,
            ),
            text=[
                f"{value:+.1f}pp"
                for value in data["Change pp"]
            ],
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b>"
                "<br>2025 share: %{customdata[0]:.1f}%"
                "<br>2026 share: %{customdata[1]:.1f}%"
                "<br>Change: %{x:+.1f}pp<extra></extra>"
            ),
        )
    )
    figure.add_vline(x=0, line_width=1, line_color="#98A2B3")
    figure.update_xaxes(title="Share change (percentage points)", ticksuffix=" pp")
    figure.update_yaxes(title="")
    figure.update_traces(textfont={"size": 11, "color": INK})
    return _apply_theme(
        figure,
        f"{'销量' if metric == 'Units' else '销额'}份额变化 · 2026 vs 2025",
        height=520,
        showlegend=False,
    )


def heatmap_chart(
    matrix: pd.DataFrame,
    metric: str,
    year: int,
) -> go.Figure:
    data = matrix.astype(float)
    text = data.map(
        lambda value: "—" if pd.isna(value) else (
            f"{value / 1_000_000:.2f}M"
            if metric == "Revenue" and abs(value) >= 1_000_000
            else f"€{value / 1_000:.1f}K"
            if metric == "Revenue"
            else f"{value:,.0f}"
        )
    )
    figure = go.Figure(
        go.Heatmap(
            z=data.to_numpy(),
            x=list(data.columns),
            y=list(data.index),
            colorscale=[
                [0.0, "#F1F5F9"],
                [0.25, "#C9D9EC"],
                [0.55, "#6FA0D4"],
                [0.8, "#2D65A3"],
                [1.0, "#0B2447"],
            ],
            text=text.to_numpy(),
            texttemplate="%{text}",
            textfont={"size": 10, "color": INK},
            hovertemplate=(
                "<b>%{y}</b> · %{x}"
                f"<br>{'Revenue' if metric == 'Revenue' else 'Units'}: "
                "%{z:,.2f}<extra></extra>"
            ),
            colorbar={
                "title": "Revenue (€)" if metric == "Revenue" else "Units",
                "thickness": 12,
                "len": 0.72,
            },
            hoverongaps=False,
        )
    )
    figure.update_xaxes(side="top")
    return _apply_theme(
        figure,
        f"{year} 年品牌 × 容量段热力图",
        height=520,
        showlegend=False,
    )


def _blend_hex(color: str, target: str, amount: float) -> str:
    def rgb(hex_color: str) -> tuple[int, int, int]:
        value = hex_color.lstrip("#")
        return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))

    source_rgb = rgb(color)
    target_rgb = rgb(target)
    mixed = tuple(
        round(source + (target - source) * amount)
        for source, target in zip(source_rgb, target_rgb, strict=True)
    )
    return "#" + "".join(f"{value:02X}" for value in mixed)


def _product_colors(product_catalog: pd.DataFrame) -> dict[str, str]:
    colors: dict[str, str] = {}
    for brand, group in product_catalog.groupby("Brand", sort=False):
        base = BRAND_COLORS.get(brand, "#64748B")
        count = len(group)
        for index, asin in enumerate(group["ASIN"].tolist()):
            amount = 0.34 * (index / max(count - 1, 1))
            colors[asin] = _blend_hex(base, "#FFFFFF", amount)
    return colors


def price_line_chart(
    price_data: pd.DataFrame,
    product_catalog: pd.DataFrame,
    selected_asins: list[str],
) -> go.Figure:
    colors = _product_colors(product_catalog)
    figure = go.Figure()
    for asin in selected_asins:
        product_rows = price_data[
            (price_data["ASIN"] == asin) & price_data["Price"].notna()
        ].sort_values("Date")
        if product_rows.empty:
            continue
        product = product_catalog[product_catalog["ASIN"] == asin].iloc[0]
        capacity_kwh = float(product["Capacity Wh"]) / 1000.0
        price_per_kwh = product_rows["Price"] / capacity_kwh
        series = str(product["Series"])
        capacity_text = f"{float(product['Capacity Wh']):,.0f} Wh"
        customdata = np.stack(
            [
                product_rows["Series"].astype(str),
                product_rows["Brand"].astype(str),
                product_rows["Product Name"].astype(str),
                product_rows["Capacity Wh"].map(lambda value: f"{value:,.0f} Wh"),
                product_rows["Date"].dt.strftime("%b %Y"),
                price_per_kwh,
            ],
            axis=-1,
        )
        figure.add_trace(
            go.Scatter(
                x=product_rows["Date"],
                y=product_rows["Price"],
                mode="lines+markers",
                name=f"{product['Brand']} · {series} · {capacity_text}",
                legendgroup=asin,
                connectgaps=False,
                line={"width": 2.1, "color": colors.get(asin, "#64748B")},
                marker={"size": 5},
                customdata=customdata,
                hovertemplate=(
                    "<b>%{customdata[1]}</b> · %{customdata[0]}"
                    "<br>Capacity: %{customdata[3]}"
                    "<br>Product: %{customdata[2]}"
                    "<br>%{customdata[4]}"
                    "<br>Price: €%{y:,.2f}"
                    "<br>€/kWh: €%{customdata[5]:,.2f}<extra></extra>"
                ),
            )
        )

    figure.update_layout(hovermode="closest")
    figure.update_xaxes(
        title="Month",
        tickformat="%b %y",
        dtick="M1",
        tickangle=-35,
    )
    figure.update_yaxes(
        title="Price (€)",
        tickprefix="€",
        rangemode="tozero",
        tickformat=",.0f",
    )
    figure = _apply_theme(
        figure,
        "核心竞品月度售价 · 缺失月份保留断点",
        height=640,
    )
    figure.update_layout(
        legend={
            "orientation": "v",
            "yanchor": "top",
            "y": 1.0,
            "xanchor": "left",
            "x": 1.02,
            "font": {"size": 9.5, "family": FONT_FAMILY},
            "itemclick": "toggle",
            "itemdoubleclick": "toggleothers",
        },
        margin={"l": 54, "r": 340, "t": 92, "b": 54},
    )
    return figure
