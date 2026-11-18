from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .config import (
    CAPACITY_SEGMENTS,
    CHART_GROUPED_BRANDS,
    FOCUS_BRANDS,
    MONTH_LABELS,
    OTHER_BRAND_LABEL,
    REPORT_YEARS,
    SHEET_NAMES,
    TARGET_PRICE_ASINS,
)


class DashboardDataError(RuntimeError):
    """Raised when the source workbook cannot support the dashboard safely."""


@dataclass
class DataQuality:
    source_sheets: list[str] = field(default_factory=list)
    asin_count: int = 0
    brand_count: int = 0
    focus_brand_count: int = 0
    other_brand_count: int = 0
    months: list[pd.Timestamp] = field(default_factory=list)
    latest_month: pd.Timestamp | None = None
    capacity_reconciles: bool = False
    capacity_max_diff: float = 0.0
    capacity_mismatch_months: int = 0
    source_segment_mismatches: int = 0
    price_zero_records: int = 0
    price_missing_cells: int = 0
    price_products_found: int = 0
    price_products_expected: int = 0
    duplicate_asin_months: int = 0
    brand_pivot_mismatch_rows: pd.DataFrame = field(default_factory=pd.DataFrame)
    issues: list[dict[str, str]] = field(default_factory=list)


@dataclass
class DashboardData:
    sales: pd.DataFrame
    prices: pd.DataFrame
    price_products: pd.DataFrame
    quality: DataQuality
    source_path: Path
    source_modified: pd.Timestamp


BRAND_ALIASES = {
    "ANKER": "Anker",
    "ECOFLOW": "ECOFLOW",
    "ECO FLOW": "ECOFLOW",
    "MARSTEK": "MARSTEK",
    "HOYMILES": "Hoymiles",
    "JACKERY": "Jackery",
    "MENTECH": "Mentech",
    "POWERNESS": "Powerness",
    "SOLAKON": "Solakon",
    "SUNNIVA": "SUNNIVA",
    "TSUN": "TSUN",
    "ZENDURE": "Zendure",
    "ZINNZGREEN": "ZINNZGREEN",
}

SERIES_PATTERNS = (
    ("SOLIX 3 PRO SOLARBANK + BP2700", "SOLIX 3 Pro + BP2700"),
    ("SOLIX SOLARBANK 3 PRO+4", "SOLIX 3 Pro + Panels"),
    ("SOLIX 2 PLUS SOLARBANK + 2", "SOLIX 2 Plus + Panels"),
    ("SOLIX SOLARBANK 3 E2700 PRO", "SOLIX 3 E2700 Pro"),
    ("SOLIX 3 E2700 PRO", "SOLIX 3 E2700 Pro"),
    ("SOLIX SOLARBANK 3 PRO", "SOLIX 3 Pro"),
    ("SOLIX 3 PRO", "SOLIX 3 Pro"),
    ("SOLIX BP1600", "SOLIX BP1600"),
    ("SOLIX 2 PLUS", "SOLIX 2 Plus"),
    ("STREAM AC PRO", "STREAM AC Pro"),
    ("STREAM ULTRA", "STREAM Ultra"),
    ("HIBATTERY AC", "HiBattery AC"),
    ("B2500", "B2500"),
    ("NOAH 2000", "NOAH 2000"),
)


def standardize_brand(value: object) -> str | pd.NA:
    if pd.isna(value):
        return pd.NA
    cleaned = re.sub(r"\s+", " ", str(value).strip())
    if not cleaned:
        return pd.NA
    alias = BRAND_ALIASES.get(cleaned.upper())
    return alias if alias else cleaned


def infer_series_name(brand: object, title: object) -> str:
    brand_text = "" if pd.isna(brand) else str(brand).strip()
    title_text = "" if pd.isna(title) else str(title).strip()
    title_upper = title_text.upper()
    for marker, label in SERIES_PATTERNS:
        if marker in title_upper:
            return label

    fallback = title_text
    if brand_text:
        fallback = re.sub(
            rf"^{re.escape(brand_text)}\s*",
            "",
            fallback,
            flags=re.IGNORECASE,
        )
    fallback = re.split(r"[+,，(]", fallback, maxsplit=1)[0].strip()
    if fallback:
        return " ".join(fallback.split()[:6])
    return brand_text or "Unknown series"


def normalize_capacity_wh(value: object) -> float:
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value) if np.isfinite(value) else np.nan

    text = str(value).strip().upper()
    if "WH" in text and "KWH" not in text:
        text = re.sub(r"(?<=\d)[.,](?=\d{3}(?:\s*WH)?$)", "", text)
    text = text.replace(",", ".")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return np.nan
    number = float(match.group())
    if "KWH" in text:
        return number * 1000.0
    return number


def assign_capacity_segment(capacity_wh: object) -> str | pd.NA:
    if pd.isna(capacity_wh):
        return pd.NA
    capacity = float(capacity_wh)
    if capacity < 2000:
        return "<2kWh"
    if capacity < 3000:
        return "2-3kWh"
    if capacity < 4000:
        return "3-4kWh"
    if capacity <= 5000:
        return "4-5kWh"
    return ">5kWh"


def month_start(value: str | pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(value).to_period("M").to_timestamp()


def month_label(value: pd.Timestamp, include_year: bool = False) -> str:
    timestamp = pd.Timestamp(value)
    label = MONTH_LABELS[timestamp.month - 1]
    return f"{label} {timestamp.year}" if include_year else label


def active_months(years: Iterable[int] | None = None) -> list[pd.Timestamp]:
    selected_years = sorted(set(years or REPORT_YEARS))
    return [
        pd.Timestamp(year=year, month=month, day=1)
        for year in selected_years
        for month in range(1, 13)
    ]


def _value_column(value: object) -> bool:
    text = str(value)
    return bool(re.fullmatch(r"\d{4}-\d{2}(?:\(€\))?", text))


def _month_from_column(value: object) -> pd.Timestamp | None:
    match = re.match(r"^(\d{4})-(\d{2})", str(value))
    if not match:
        return None
    return pd.Timestamp(year=int(match.group(1)), month=int(match.group(2)), day=1)


def _read_history(path: Path, sheet_name: str) -> pd.DataFrame:
    try:
        frame = pd.read_excel(path, sheet_name=sheet_name, header=0)
    except ValueError as exc:
        raise DashboardDataError(
            f"缺少工作表“{sheet_name}”。请检查源文件结构。"
        ) from exc

    rename_map: dict[object, str] = {}
    for column in frame.columns:
        text = str(column).strip()
        if text.upper() == "ASIN":
            rename_map[column] = "ASIN"
        elif text.upper() == "BRAND" or text == "品牌":
            rename_map[column] = "Brand"
        elif text == "商品标题":
            rename_map[column] = "Product Name"
    frame = frame.rename(columns=rename_map)

    missing = {"ASIN", "Brand", "Product Name"} - set(frame.columns)
    if missing:
        raise DashboardDataError(
            f"工作表“{sheet_name}”缺少必要字段：{', '.join(sorted(missing))}"
        )

    capacity_columns = [
        column
        for column in frame.columns
        if str(column).strip().startswith("容量")
        and str(column).strip() != "容量段"
    ]
    capacities = pd.concat(
        [
            frame[column].map(normalize_capacity_wh)
            for column in capacity_columns
        ],
        axis=1,
    )
    frame["Capacity Wh"] = capacities.bfill(axis=1).iloc[:, -1]
    frame["Brand"] = frame["Brand"].map(standardize_brand).astype("string")
    frame["ASIN"] = frame["ASIN"].astype("string").str.strip()
    frame["Product Name"] = frame["Product Name"].fillna("").astype(str).str.strip()

    month_columns = [column for column in frame.columns if _value_column(column)]
    if not month_columns:
        raise DashboardDataError(
            f"工作表“{sheet_name}”中未识别到 2025/2026 月度字段。"
        )

    id_columns = ["ASIN", "Brand", "Product Name", "Capacity Wh"]
    long = frame[id_columns + month_columns].melt(
        id_vars=id_columns,
        value_vars=month_columns,
        var_name="Month Column",
        value_name="Value",
    )
    long["Date"] = long["Month Column"].map(_month_from_column)
    long = long[long["Date"].dt.year.isin(REPORT_YEARS)].copy()
    long["Value"] = pd.to_numeric(long["Value"], errors="coerce")
    long["Year"] = long["Date"].dt.year.astype(int)
    long["Month Number"] = long["Date"].dt.month.astype(int)
    long["Month Label"] = long["Date"].map(month_label)
    long = long.loc[:, ["ASIN", "Brand", "Product Name", "Capacity Wh", "Date", "Year", "Month Number", "Month Label", "Value"]]
    return long


def _read_crosstab(path: Path, sheet_name: str, header_row: int) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    if header_row >= len(raw):
        raise DashboardDataError(f"工作表“{sheet_name}”表头位置异常。")
    body = raw.iloc[header_row + 1 :].copy()
    body.columns = raw.iloc[header_row].tolist()
    body = body[body.iloc[:, 0].notna()].copy()
    body = body.loc[
        :,
        [body.columns[0]]
        + [column for column in body.columns[1:] if pd.notna(column)],
    ]
    body = body.rename(columns={body.columns[0]: "Label"})
    for column in body.columns[1:]:
        body[column] = pd.to_numeric(body[column], errors="coerce")
    return body


def _crosstab_to_long(
    frame: pd.DataFrame,
    dimension: str,
) -> pd.DataFrame:
    month_columns = [
        column
        for column in frame.columns[1:]
        if isinstance(column, str) and column.startswith("求和项:")
    ]
    if not month_columns:
        raise DashboardDataError(f"{dimension} 汇总表未识别到月度字段。")
    long = frame.loc[:, ["Label", *month_columns]].melt(
        id_vars="Label",
        value_vars=month_columns,
        var_name="Month Column",
        value_name="Units",
    )
    long["Date"] = long["Month Column"].str.replace("求和项:", "", regex=False).map(
        lambda value: pd.Timestamp(f"{value}-01")
    )
    long = long[long["Date"].dt.year.isin(REPORT_YEARS)].copy()
    long[dimension] = long["Label"].astype(str).str.strip()
    return long.drop(columns=["Label", "Month Column"])


def _grouped_sum(
    frame: pd.DataFrame,
    group_columns: list[str],
    value_column: str,
) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=float)
    return frame.groupby(group_columns, dropna=False)[value_column].sum(min_count=1)


def load_dashboard_data(data_path: Path | str) -> DashboardData:
    path = Path(data_path).resolve()
    if not path.exists():
        raise DashboardDataError(
            f"未找到数据文件：{path}。请将 Excel 放入 dashboard/data/，"
            "或设置 BALCONY_DATA_PATH。"
        )

    try:
        source_sheets = pd.ExcelFile(path).sheet_names
    except Exception as exc:
        raise DashboardDataError(f"无法读取 Excel：{exc}") from exc

    required_sheets = set(SHEET_NAMES.values())
    missing_sheets = required_sheets - set(source_sheets)
    if missing_sheets:
        raise DashboardDataError(
            "源文件缺少工作表：" + "、".join(sorted(missing_sheets))
        )

    units_long = _read_history(path, SHEET_NAMES["units"]).rename(
        columns={"Value": "Units"}
    )
    revenue_long = _read_history(path, SHEET_NAMES["revenue"]).rename(
        columns={"Value": "Revenue"}
    )
    price_long = _read_history(path, SHEET_NAMES["prices"]).rename(
        columns={"Value": "Price"}
    )

    join_keys = ["ASIN", "Date"]
    duplicate_units = int(units_long.duplicated(join_keys).sum())
    duplicate_revenue = int(revenue_long.duplicated(join_keys).sum())
    duplicate_prices = int(price_long.duplicated(join_keys).sum())
    if duplicate_units or duplicate_revenue or duplicate_prices:
        raise DashboardDataError(
            "检测到 ASIN × 月份重复记录。为防止销量虚高，看板已停止计算："
            f"销量重复 {duplicate_units}，销额重复 {duplicate_revenue}，"
            f"价格重复 {duplicate_prices}。"
        )

    sales = units_long.merge(
        revenue_long[["ASIN", "Date", "Revenue"]],
        on=join_keys,
        how="left",
        validate="one_to_one",
    )
    price_columns = [
        "ASIN",
        "Brand",
        "Product Name",
        "Capacity Wh",
        "Date",
        "Year",
        "Month Number",
        "Month Label",
        "Price",
    ]
    prices = price_long[price_columns].merge(
        sales[
            [
                "ASIN",
                "Date",
                "Revenue",
            ]
        ],
        on=join_keys,
        how="left",
        validate="one_to_one",
    )

    raw_segment_frame = pd.read_excel(
        path, sheet_name=SHEET_NAMES["units"], header=0
    )
    raw_segment_frame = raw_segment_frame.rename(columns={"ASIN": "ASIN"})

    for frame in (sales, prices):
        frame["Capacity Segment"] = frame["Capacity Wh"].map(
            assign_capacity_segment
        ).astype("string")
        frame["Is Focus Brand"] = frame["Brand"].isin(FOCUS_BRANDS)
        frame["Brand Display"] = frame["Brand"].where(
            frame["Is Focus Brand"], OTHER_BRAND_LABEL
        )
        if "Price" in frame.columns:
            frame["Price"] = pd.to_numeric(frame["Price"], errors="coerce")
        frame["Series"] = [
            infer_series_name(brand, title)
            for brand, title in zip(
                frame["Brand"],
                frame["Product Name"],
                strict=True,
            )
        ]

    target_price_mask = prices["ASIN"].isin(TARGET_PRICE_ASINS)
    price_zero_mask = prices["Price"].notna() & (prices["Price"] <= 0)
    price_zero_records = int((price_zero_mask & target_price_mask).sum())
    prices.loc[price_zero_mask, "Price"] = np.nan

    price_products = (
        prices[prices["ASIN"].isin(TARGET_PRICE_ASINS)]
        .sort_values(["Brand", "ASIN"])
        .drop_duplicates("ASIN")
        .loc[
            :,
            [
                "ASIN",
                "Brand",
                "Series",
                "Product Name",
                "Capacity Wh",
                "Capacity Segment",
            ],
        ]
        .reset_index(drop=True)
    )
    price_products["Product Label"] = [
        f"{brand} · {series} · {capacity:,.0f} Wh"
        for brand, series, capacity in zip(
            price_products["Brand"],
            price_products["Series"],
            price_products["Capacity Wh"],
            strict=True,
        )
    ]
    target_prices = prices[prices["ASIN"].isin(TARGET_PRICE_ASINS)]

    capacity_tables = pd.concat(
        [
            _crosstab_to_long(
                _read_crosstab(path, SHEET_NAMES["capacity_2025"], 2),
                "Capacity Segment",
            ),
            _crosstab_to_long(
                _read_crosstab(path, SHEET_NAMES["capacity_2026"], 2),
                "Capacity Segment",
            ),
        ],
        ignore_index=True,
    )
    capacity_tables = capacity_tables[
        capacity_tables["Capacity Segment"].isin(CAPACITY_SEGMENTS)
    ]
    capacity_pivot = (
        capacity_tables.groupby("Date")["Units"].sum(min_count=1).sort_index()
    )
    detail_market = (
        sales.groupby("Date")["Units"].sum(min_count=1).sort_index()
    )
    comparison = pd.concat(
        [
            capacity_pivot.rename("Capacity sheet"),
            detail_market.rename("ASIN detail"),
        ],
        axis=1,
    )
    comparison["Difference"] = comparison["ASIN detail"] - comparison["Capacity sheet"]
    if capacity_pivot.empty and detail_market.empty:
        capacity_reconciles = True
    else:
        capacity_reconciles = bool(
            comparison["Difference"].dropna().abs().max() < 1e-9
        )
    capacity_max_diff = float(comparison["Difference"].abs().max())
    capacity_mismatch_months = int((comparison["Difference"].abs() >= 1e-9).sum())

    brand_tables = pd.concat(
        [
            _crosstab_to_long(
                _read_crosstab(path, SHEET_NAMES["brand_2025"], 2),
                "Brand",
            ),
            _crosstab_to_long(
                _read_crosstab(path, SHEET_NAMES["brand_2026"], 0),
                "Brand",
            ),
        ],
        ignore_index=True,
    )
    brand_tables["Brand"] = brand_tables["Brand"].map(standardize_brand)
    brand_tables = brand_tables[brand_tables["Brand"].isin(FOCUS_BRANDS)]
    detail_focus = sales[sales["Is Focus Brand"]]
    detail_focus_units = (
        detail_focus.groupby(["Brand", "Date"])["Units"]
        .sum(min_count=1)
        .rename("ASIN detail")
        .reset_index()
    )
    brand_pivot = brand_tables.rename(columns={"Units": "Brand sheet"})
    brand_comparison = brand_pivot.merge(
        detail_focus_units,
        on=["Brand", "Date"],
        how="outer",
    )
    brand_comparison["Difference"] = (
        brand_comparison["ASIN detail"] - brand_comparison["Brand sheet"]
    )
    brand_pivot_mismatch_rows = brand_comparison[
        brand_comparison["Difference"].abs().fillna(0) >= 1e-9
    ].copy()

    capacity_source_lookup = (
        raw_segment_frame[["ASIN", "容量段"]]
        .drop_duplicates("ASIN")
        .rename(columns={"容量段": "Source Segment"})
    )
    capacity_check = (
        sales.drop_duplicates("ASIN")[["ASIN", "Capacity Segment"]]
        .merge(capacity_source_lookup, on="ASIN", how="left")
    )
    source_segment_mismatches = int(
        (
            capacity_check["Capacity Segment"].fillna("")
            != capacity_check["Source Segment"].fillna("")
        ).sum()
    )

    all_dates = sorted(sales["Date"].dropna().unique())
    latest_month = pd.Timestamp(all_dates[-1]) if all_dates else None
    price_missing_cells = int(target_prices["Price"].isna().sum())

    issues: list[dict[str, str]] = [
        {
            "Severity": "Info",
            "Area": "时间覆盖",
            "Finding": "当前数据覆盖 2025-01 至 2026-10；2026 年 11–12 月尚未提供。",
            "Impact": "2026 年对比和 KPI 为年初至今口径。",
            "Handling": "图表不补造 11–12 月数据，市场对比使用份额而非全年总量。",
        },
        {
            "Severity": "Info",
            "Area": "品牌覆盖",
            "Finding": f"源文件包含 {sales['Brand'].nunique()} 个品牌；其中 12 个重点品牌单列，其余归入 Other brands。",
            "Impact": "品牌图可同时保持重点品牌可读性并让市场份额之和达到 100%。",
            "Handling": "Other brands 是源数据中的真实品牌聚合，不生成或估算记录。",
        },
        {
            "Severity": "Warning",
            "Area": "容量标准化",
            "Finding": f"按业务边界重算容量段后，有 {source_segment_mismatches} 个 ASIN 与源表容量段不同，主要是 2000Wh 产品。",
            "Impact": "容量段模块若沿用源表标签会违反互斥边界。",
            "Handling": "看板统一按“2000Wh 归入 2–3kWh”重算，源标签保留在检查记录中。",
        },
        {
            "Severity": "Info",
            "Area": "价格缺失",
            "Finding": "价格历史按 ASIN × 月份保留；产品上市前、下架后或未采集月份留空。",
            "Impact": "折线在缺失月份断开，不跨月插值。",
            "Handling": "缺失价格不填 0；0€ 价格视为不可用价格，不进入价格统计。",
        },
    ]
    if price_zero_records:
        issues.append(
            {
                "Severity": "Warning",
                "Area": "价格异常",
                "Finding": f"目标价格产品中检测到 {price_zero_records} 条 0€ 价格记录。",
                "Impact": "0€ 不是有效商业售价，若保留会扭曲均价和降价幅度。",
                "Handling": "价格分析将其视为不可用，不参与折线、均价、最低价和变化率；记录数保留在质量检查中。",
            }
        )
    if not capacity_reconciles:
        issues.append(
            {
                "Severity": "Error",
                "Area": "销量对账",
                "Finding": "ASIN 明细与容量段汇总表未完全一致。",
                "Impact": "市场总量可能出现口径差异。",
                "Handling": "看板继续展示明细来源，并在质量区显示差异月份。",
            }
        )
    if not brand_pivot_mismatch_rows.empty:
        issues.append(
            {
                "Severity": "Warning",
                "Area": "品牌汇总对账",
                "Finding": f"品牌汇总表与 ASIN 明细存在 {len(brand_pivot_mismatch_rows)} 条差异记录。",
                "Impact": "个别品牌月度销量可能因源表对账差异而略有不同。",
                "Handling": "看板以可下钻的 ASIN 明细为主口径，避免混用两个总量来源。",
            }
        )

    quality = DataQuality(
        source_sheets=source_sheets,
        asin_count=int(sales["ASIN"].nunique()),
        brand_count=int(sales["Brand"].nunique()),
        focus_brand_count=len(FOCUS_BRANDS),
        other_brand_count=max(int(sales["Brand"].nunique()) - len(FOCUS_BRANDS), 0),
        months=[pd.Timestamp(date) for date in all_dates],
        latest_month=latest_month,
        capacity_reconciles=capacity_reconciles,
        capacity_max_diff=capacity_max_diff,
        capacity_mismatch_months=capacity_mismatch_months,
        source_segment_mismatches=source_segment_mismatches,
        price_zero_records=price_zero_records,
        price_missing_cells=price_missing_cells,
        price_products_found=int(price_products["ASIN"].nunique()),
        price_products_expected=len(TARGET_PRICE_ASINS),
        duplicate_asin_months=duplicate_units + duplicate_revenue + duplicate_prices,
        brand_pivot_mismatch_rows=brand_pivot_mismatch_rows.sort_values(
            ["Date", "Brand"]
        ),
        issues=issues,
    )

    return DashboardData(
        sales=sales,
        prices=prices,
        price_products=price_products,
        quality=quality,
        source_path=path,
        source_modified=pd.Timestamp.fromtimestamp(path.stat().st_mtime),
    )


def filter_sales(
    sales: pd.DataFrame,
    years: Iterable[int] | None = None,
    brands: Iterable[str] | None = None,
    capacity_segments: Iterable[str] | None = None,
) -> pd.DataFrame:
    filtered = sales.copy()
    if years is not None:
        filtered = filtered[filtered["Year"].isin(list(years))]
    if brands is not None:
        filtered = filtered[filtered["Brand Display"].isin(list(brands))]
    if capacity_segments is not None:
        filtered = filtered[
            filtered["Capacity Segment"].isin(list(capacity_segments))
        ]
    return filtered


def prepare_brand_chart_data(
    sales: pd.DataFrame,
    selected_brands: Iterable[str],
) -> tuple[pd.DataFrame, list[str]]:
    selected = list(selected_brands)
    grouped = set(CHART_GROUPED_BRANDS)
    chart_sales = sales.copy()
    chart_sales["Chart Brand"] = chart_sales["Brand Display"].where(
        ~chart_sales["Brand Display"].isin(grouped),
        OTHER_BRAND_LABEL,
    )
    categories = [
        brand for brand in selected if brand not in grouped
    ]
    if (
        OTHER_BRAND_LABEL in selected
        or any(brand in grouped for brand in selected)
    ):
        categories.append(OTHER_BRAND_LABEL)
    categories = list(dict.fromkeys(categories))
    return chart_sales, categories


def filter_prices(
    prices: pd.DataFrame,
    years: Iterable[int] | None = None,
    brands: Iterable[str] | None = None,
    capacity_segments: Iterable[str] | None = None,
    asins: Iterable[str] | None = None,
) -> pd.DataFrame:
    filtered = prices[prices["ASIN"].isin(TARGET_PRICE_ASINS)].copy()
    if years is not None:
        filtered = filtered[filtered["Year"].isin(list(years))]
    if brands is not None:
        filtered = filtered[filtered["Brand"].isin(list(brands))]
    if capacity_segments is not None:
        filtered = filtered[
            filtered["Capacity Segment"].isin(list(capacity_segments))
        ]
    if asins is not None:
        filtered = filtered[filtered["ASIN"].isin(list(asins))]
    return filtered


def summarize_sales(sales: pd.DataFrame) -> tuple[float | None, float | None]:
    units = sales["Units"].sum(min_count=1) if not sales.empty else None
    revenue = sales["Revenue"].sum(min_count=1) if not sales.empty else None
    return (
        float(units) if pd.notna(units) else None,
        float(revenue) if pd.notna(revenue) else None,
    )


def monthly_dimension_pivot(
    sales: pd.DataFrame,
    dimension: str,
    metric: str,
    categories: Iterable[str],
    years: Iterable[int] | None = None,
) -> pd.DataFrame:
    dates = active_months(years)
    if sales.empty:
        return pd.DataFrame(index=dates, columns=list(categories), dtype=float)
    grouped = (
        sales.groupby(["Date", dimension], dropna=False)[metric]
        .sum(min_count=1)
        .reset_index()
    )
    pivot = grouped.pivot(index="Date", columns=dimension, values=metric)
    return pivot.reindex(index=dates, columns=list(categories))


def market_share_table(
    sales: pd.DataFrame,
    year: int,
    dimension: str,
    metric: str,
    categories: Iterable[str],
) -> pd.DataFrame:
    scope = sales[sales["Year"] == year]
    grouped = scope.groupby(dimension, dropna=False).agg(
        Units=("Units", lambda values: values.sum(min_count=1)),
        Revenue=("Revenue", lambda values: values.sum(min_count=1)),
    )
    grouped = grouped.reindex(list(categories))
    metric_totals = scope.groupby(dimension)[metric].sum(min_count=1)
    total = metric_totals.sum(min_count=1)
    grouped["Value"] = grouped[metric]
    grouped["Share"] = (
        grouped["Value"] / total * 100 if pd.notna(total) and total != 0 else np.nan
    )
    grouped["Year"] = year
    return grouped.reset_index().rename(columns={dimension: "Category"})


def share_change_table(
    sales: pd.DataFrame,
    dimension: str,
    metric: str,
    categories: Iterable[str],
    base_year: int = 2025,
    compare_year: int = 2026,
) -> pd.DataFrame:
    base = market_share_table(sales, base_year, dimension, metric, categories)
    compare = market_share_table(sales, compare_year, dimension, metric, categories)
    merged = base[["Category", "Share"]].rename(columns={"Share": "2025 Share"})
    merged = merged.merge(
        compare[["Category", "Share"]].rename(columns={"Share": "2026 Share"}),
        on="Category",
        how="outer",
    )
    merged["Change pp"] = merged["2026 Share"] - merged["2025 Share"]
    merged["Abs Change"] = merged["Change pp"].abs()
    return merged.sort_values(
        ["Abs Change", "Category"], ascending=[False, True], na_position="last"
    )


def heatmap_table(
    sales: pd.DataFrame,
    year: int,
    metric: str,
    brands: Iterable[str],
    segments: Iterable[str],
) -> pd.DataFrame:
    scope = sales[sales["Year"] == year]
    table = (
        scope.groupby(["Brand Display", "Capacity Segment"])[metric]
        .sum(min_count=1)
        .unstack("Capacity Segment")
    )
    return table.reindex(index=list(brands), columns=list(segments))


def build_price_summary(
    price_data: pd.DataFrame,
    product_catalog: pd.DataFrame,
    selected_brands: Iterable[str] | None = None,
    selected_segments: Iterable[str] | None = None,
    selected_asins: Iterable[str] | None = None,
) -> pd.DataFrame:
    catalog = product_catalog.copy()
    if selected_brands is not None:
        catalog = catalog[catalog["Brand"].isin(list(selected_brands))]
    if selected_segments is not None:
        catalog = catalog[
            catalog["Capacity Segment"].isin(list(selected_segments))
        ]
    if selected_asins is not None:
        catalog = catalog[catalog["ASIN"].isin(list(selected_asins))]

    rows: list[dict[str, object]] = []
    for _, product in catalog.iterrows():
        product_rows = price_data[
            (price_data["ASIN"] == product["ASIN"]) & price_data["Price"].notna()
        ].sort_values("Date")
        if product_rows.empty:
            latest_date = pd.NaT
            latest_price = np.nan
            previous_price = np.nan
            average_price = np.nan
            minimum_price = np.nan
            maximum_price = np.nan
        else:
            latest_row = product_rows.iloc[-1]
            latest_date = pd.Timestamp(latest_row["Date"])
            latest_price = float(latest_row["Price"])
            previous_date = latest_date - pd.DateOffset(months=1)
            previous_rows = product_rows[product_rows["Date"] == previous_date]
            previous_price = (
                float(previous_rows.iloc[-1]["Price"])
                if not previous_rows.empty
                else np.nan
            )
            average_price = float(product_rows["Price"].mean())
            minimum_price = float(product_rows["Price"].min())
            maximum_price = float(product_rows["Price"].max())

        if pd.notna(previous_price) and previous_price != 0 and pd.notna(latest_price):
            change_rate = (latest_price - previous_price) / previous_price * 100
        else:
            change_rate = np.nan

        capacity_kwh = float(product["Capacity Wh"]) / 1000.0
        rows.append(
            {
                "ASIN": product["ASIN"],
                "Brand": product["Brand"],
                "Series": product["Series"],
                "Product Name": product["Product Name"],
                "Capacity Wh": float(product["Capacity Wh"]),
                "Capacity Segment": product["Capacity Segment"],
                "Average Price": average_price,
                "Minimum Price": minimum_price,
                "Maximum Price": maximum_price,
                "Latest Month": latest_date,
                "Latest Price": latest_price,
                "Previous Month Price": previous_price,
                "Price Change (%)": change_rate,
                "Price per kWh": (
                    latest_price / capacity_kwh
                    if pd.notna(latest_price) and capacity_kwh > 0
                    else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)
