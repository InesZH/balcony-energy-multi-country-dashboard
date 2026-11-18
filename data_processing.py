from __future__ import annotations

import colorsys
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from config import (
    ANALYSIS_YEARS,
    BRAND_COLORS,
    BRAND_FALLBACK_COLORS,
    EXCLUDED_BRANDS,
    PRODUCT_OVERRIDES_FILE,
    SEGMENT_COLORS,
    SEGMENT_ORDER,
    SHEET_CANDIDATES,
    UNKNOWN_SEGMENT,
    resolve_source_file,
)


MONTH_PATTERN = re.compile(r"^(\d{4})-(\d{2})(?:\(€\))?$")
WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass
class QualityIssue:
    level: str
    category: str
    title: str
    detail: str


@dataclass
class DashboardData:
    source_path: Path
    source_modified: datetime
    market_long: pd.DataFrame
    product_master: pd.DataFrame
    product_catalog: pd.DataFrame
    price_long: pd.DataFrame
    quality_issues: list[QualityIssue] = field(default_factory=list)
    validation_notes: list[str] = field(default_factory=list)
    latest_market_month: str | None = None
    latest_price_month: str | None = None

    @property
    def market_brands(self) -> list[str]:
        return sorted(
            self.market_long["brand"].dropna().astype(str).unique().tolist()
        )

    @property
    def price_brands(self) -> list[str]:
        return sorted(
            self.product_catalog["brand"].dropna().astype(str).unique().tolist()
        )

    @property
    def market_segments(self) -> list[str]:
        present = set(
            self.market_long["capacity_segment"].dropna().astype(str).unique()
        )
        return [segment for segment in SEGMENT_ORDER if segment in present]

    @property
    def price_segments(self) -> list[str]:
        present = set(
            self.product_catalog["capacity_segment"]
            .dropna()
            .astype(str)
            .unique()
        )
        return [
            segment
            for segment in (*SEGMENT_ORDER, UNKNOWN_SEGMENT)
            if segment in present
        ]


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return WHITESPACE_PATTERN.sub(" ", str(value).replace("\u00a0", " ")).strip()


def standardize_brand(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""
    compact = re.sub(r"[^A-Z0-9]", "", text.upper())
    if "ZENDURE" in compact:
        return "Zendure"
    if "ECOFLOW" in compact:
        return "EcoFlow"
    if "ANKER" in compact:
        return "Anker"
    if "MARSTEK" in compact:
        return "Marstek"
    if "JACKERY" in compact:
        return "Jackery"
    if "FOSSIBOT" in compact:
        return "FOSSiBOT"
    if "STORCUBE" in compact:
        return "STORCUBE"
    if "BIGBLUE" in compact:
        return "BigBlue"
    if "SAMDUO" in compact:
        return "SAMDUO"
    if "HOYMILES" in compact:
        return "Hoymiles"
    if "GREENSUN" in compact:
        return "GreenSun Solar"
    if compact == "DJI":
        return "DJI"
    if "INDEVOLT" in compact:
        return "Indevolt"
    return text


def infer_brand_from_title(title: object) -> str:
    text = clean_text(title)
    for token in (
        "Zendure",
        "EcoFlow",
        "ECOFLOW",
        "Anker",
        "Marstek",
        "Jackery",
        "FOSSiBOT",
        "STORCUBE",
        "BigBlue",
        "SAMDUO",
        "Hoymiles",
        "DJI",
        "Indevolt",
    ):
        if token.casefold() in text.casefold():
            return standardize_brand(token)
    return ""


def _parse_number(text: str) -> float:
    normalized = (
        clean_text(text)
        .replace("\u202f", "")
        .replace(" ", "")
        .replace(",", ".")
    )
    if normalized.count(".") > 1:
        parts = normalized.split(".")
        normalized = "".join(parts[:-1]) + "." + parts[-1]
    return float(normalized)


def normalize_capacity_wh(value: object) -> float:
    if value is None or pd.isna(value) or clean_text(value) == "":
        return np.nan

    if isinstance(value, (int, float, np.integer, np.floating)):
        numeric = float(value)
        if numeric <= 0:
            return np.nan
        # 独立容量字段偶尔可能使用 kWh。Wh 数据通常为数百至数万。
        if numeric < 50:
            numeric *= 1000
        return numeric

    text = clean_text(value)
    lower = text.casefold()
    match = re.search(
        r"(\d{1,3}(?:[\s\u202f]\d{3})+|\d+(?:[.,]\d+)?)\s*(kwh|wh)\b",
        lower,
    )
    if match:
        number = _parse_number(match.group(1))
        return number * 1000 if match.group(2) == "kwh" else number

    numeric_match = re.search(r"\d+(?:[.,]\d+)?", text)
    if not numeric_match:
        return np.nan
    numeric = _parse_number(numeric_match.group(0))
    if numeric <= 0:
        return np.nan
    return numeric * 1000 if numeric < 50 else numeric


def extract_explicit_capacity_wh(title: object) -> float:
    text = clean_text(title)
    pattern = re.compile(
        r"(?<![\d.,])(\d{1,3}(?:[\s\u202f]\d{3})+|\d+(?:[.,]\d+)?)"
        r"\s*(kwh|wh)\b",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        context = text[
            max(0, match.start() - 35) : min(len(text), match.end() + 45)
        ].casefold()
        if any(
            marker in context
            for marker in (
                "extensible",
                "extendable",
                "capacité ext",
                "capacite ext",
                "capacité max",
                "capacity max",
                "jusqu'à",
                "up to",
            )
        ):
            continue
        number = _parse_number(match.group(1))
        capacity = number * 1000 if match.group(2).casefold() == "kwh" else number
        if 100 <= capacity <= 100_000:
            return capacity
    return np.nan


def capacity_segment(capacity_wh: object) -> str:
    try:
        capacity = float(capacity_wh)
    except (TypeError, ValueError):
        return UNKNOWN_SEGMENT
    if pd.isna(capacity) or capacity <= 0:
        return UNKNOWN_SEGMENT
    if capacity < 2000:
        return "<2kWh"
    if capacity < 3000:
        return "2–3kWh"
    if capacity < 4000:
        return "3–4kWh"
    if capacity <= 5000:
        return "4–5kWh"
    return ">5kWh"


def format_capacity(capacity_wh: object) -> str:
    try:
        capacity = float(capacity_wh)
    except (TypeError, ValueError):
        return ""
    if pd.isna(capacity) or capacity <= 0:
        return ""
    kwh = capacity / 1000
    if abs(kwh - round(kwh)) < 1e-9:
        return f"{int(round(kwh))}kWh"
    return f"{kwh:.3f}".rstrip("0").rstrip(".") + "kWh"


def extract_series(title: object, brand: str) -> str:
    text = clean_text(title)
    lower = text.casefold()

    if brand == "Anker":
        match = re.search(
            r"SOLIX\s+(Solarbank\s+(?:\d+\s+)?[^,;|(]+|BP\d+)",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            series = clean_text(match.group(0))
            series = re.sub(
                r"\s+(?:batterie|station|système)\b.*$",
                "",
                series,
                flags=re.IGNORECASE,
            )
            return series

    if brand == "Zendure":
        zendure_patterns = (
            (r"Solar\s*Flow\s+2400\s+Pro", "SolarFlow 2400 Pro"),
            (r"Solar\s*Flow\s+2400\s+AC", "SolarFlow 2400 AC"),
            (r"Solar\s*Flow\s+800\s+Pro2", "SolarFlow 800 Pro2"),
            (r"Solar\s*Flow\s+800\s+Plus", "SolarFlow 800 Plus"),
            (r"Solar\s*Flow\s+800\s+Pro\b", "SolarFlow 800 Pro"),
            (r"Solar\s*Flow\s+Hyper\s+2000", "SolarFlow Hyper 2000"),
            (r"Solar\s*Flow\s+AIO\s+Pro\s+1200", "SolarFlow AIO Pro 1200"),
            (r"Solar\s*Flow\s+AB3000X", "SolarFlow AB3000X"),
            (r"SF800\s+Pro2", "SF800 Pro2"),
        )
        for pattern, canonical in zendure_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return canonical

    if brand == "EcoFlow":
        ecoflow_patterns = (
            (r"STREAM\s+AC\s+Pro", "STREAM AC Pro"),
            (r"STREAM\s+Ultra\s*[Xx×*]\s*2", "STREAM Ultra ×2"),
            (r"STREAM\s+Ultra\s+X", "STREAM Ultra X"),
            (r"STREAM\s+Ultra", "STREAM Ultra"),
            (r"STREAM\s+Pro", "STREAM Pro"),
            (r"STREAM\s+AC\s+5000", "STREAM AC 5000"),
            (r"STREAM\s+5000", "STREAM 5000"),
            (r"STREAM\s+AC", "STREAM AC"),
        )
        for pattern, canonical in ecoflow_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return canonical

    fixed_series = (
        ("STORCUBE", r"S1000\s*PRO", "S1000PRO"),
        ("STORCUBE", r"\bS1000\b", "S1000"),
        ("FOSSiBOT", r"FBP1200", "FBP1200"),
        ("Marstek", r"Venus\s+E\s+3\.0", "Venus E 3.0"),
        ("Jackery", r"SolarVault\s+3\s+Pro\s+Max", "SolarVault 3 Pro Max"),
        ("SAMDUO", r"Nex\s+E6000", "Nex E6000"),
        ("BigBlue", r"Powafree", "Powafree"),
        ("Hoymiles", r"HiBattery\s+AC", "HiBattery AC"),
        ("DJI", r"Power\s+1000\s+V2", "Power 1000 V2"),
        ("Indevolt", r"SolidFlex\s+3000", "SolidFlex 3000"),
    )
    for expected_brand, pattern, series in fixed_series:
        if brand in ("", expected_brand) and re.search(
            pattern, text, flags=re.IGNORECASE
        ):
            return series

    if brand == "GreenSun Solar" and "marstek venus e 3.0" in lower:
        return "Venus E 3.0"

    fallback = re.split(r"[,;|(]", text, maxsplit=1)[0]
    for prefix in (
        "EF ECOFLOW",
        "ECOFLOW",
        "EcoFlow",
        "ZENDURE SuperCharged",
        "ZENDURE",
        "Zendure",
        "Anker",
        "Marstek",
        "Jackery",
        "FOSSiBOT",
        "BigBlue",
        "SAMDUO",
        "Hoymiles",
        "DJI",
        "Indevolt",
    ):
        fallback = re.sub(
            rf"^\s*{re.escape(prefix)}\s*",
            "",
            fallback,
            flags=re.IGNORECASE,
        )
    return clean_text(fallback)[:70]


def build_product_name(
    brand: str,
    series: str,
    capacity_wh: object,
    title: str,
    override: str = "",
) -> str:
    if override:
        return override
    capacity = format_capacity(capacity_wh)
    if brand and series:
        base = f"{brand} {series}"
    elif brand:
        base = f"{brand} {clean_text(title)[:70]}"
    else:
        base = clean_text(title)[:90]
    return f"{base} – {capacity}" if capacity else base


def shorten_product_name(name: str, max_chars: int = 58) -> str:
    if len(name) <= max_chars:
        return name
    brand, separator, rest = name.partition(" ")
    if not separator:
        return name[: max_chars - 1] + "…"
    capacity_separator = " – "
    capacity = ""
    if capacity_separator in rest:
        rest, capacity_part = rest.rsplit(capacity_separator, 1)
        capacity = capacity_separator + capacity_part
    remaining = max_chars - len(brand) - 1 - len(capacity) - 1
    if remaining < 12:
        return (brand + capacity)[:max_chars]
    return f"{brand} {rest[:remaining].rstrip()}…{capacity}"


def extract_variant_hint(title: object, sku: object) -> str:
    sku_text = clean_text(sku)
    if sku_text:
        hint = re.sub(
            r"^(?:Style|Taille|Set name)\s*:\s*",
            "",
            sku_text,
            flags=re.IGNORECASE,
        )
        hint = re.sub(r"\s+", " ", hint).strip(" -+")
        if hint:
            return hint[:34]

    text = clean_text(title)
    lower = text.casefold()
    if "recondition" in lower:
        return "Reconditionné"

    battery_match = re.search(
        r"(?:\d+\s*[x×*]\s*AB\d+[A-Z]*|AB\d+[A-Z]*\s*[x×*]\s*\d+)",
        text,
        flags=re.IGNORECASE,
    )
    if battery_match:
        return re.sub(r"\s+", "", battery_match.group(0)).replace("*", "×")

    panel_match = re.search(
        r"(?:Panneau(?:x)?\s+Solaire|Panels?)\s+(\d+(?:[.,]\d+)?)\s*W",
        text,
        flags=re.IGNORECASE,
    )
    if panel_match:
        return f"Panel {panel_match.group(1)}W"

    panel_set_match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*[x×*]\s*(\d+(?:[.,]\d+)?)\s*W",
        text,
        flags=re.IGNORECASE,
    )
    if panel_set_match:
        return f"{panel_set_match.group(1)}×{panel_set_match.group(2)}W panels"
    return ""


def _hex_to_rgb(color: str) -> tuple[float, float, float]:
    color = color.lstrip("#")
    return tuple(int(color[index : index + 2], 16) / 255 for index in (0, 2, 4))


def _rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(
        f"{max(0, min(255, round(channel * 255))):02X}" for channel in rgb
    )


def brand_color_map(brands: Iterable[str]) -> dict[str, str]:
    result = dict(BRAND_COLORS)
    fallback_index = 0
    for brand in sorted(set(brands)):
        if brand in result:
            continue
        result[brand] = BRAND_FALLBACK_COLORS[
            fallback_index % len(BRAND_FALLBACK_COLORS)
        ]
        fallback_index += 1
    return result


def product_color(brand: str, asin: str, colors: dict[str, str]) -> str:
    base = colors.get(brand, BRAND_FALLBACK_COLORS[0])
    red, green, blue = _hex_to_rgb(base)
    hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
    digest = hashlib.md5(asin.encode("utf-8")).hexdigest()
    bucket = int(digest[:2], 16) % 7
    adjustments = (-0.10, -0.06, -0.03, 0.0, 0.03, 0.07, 0.11)
    lightness = max(0.24, min(0.68, lightness + adjustments[bucket]))
    saturation = max(0.30, min(0.62, saturation + (bucket % 3 - 1) * 0.04))
    return _rgb_to_hex(colorsys.hls_to_rgb(hue, lightness, saturation))


def month_columns(frame: pd.DataFrame) -> list[str]:
    return [
        column
        for column in frame.columns
        if MONTH_PATTERN.match(str(column).strip())
    ]


def month_string(column: object) -> str:
    match = MONTH_PATTERN.match(str(column).strip())
    if not match:
        raise ValueError(f"无法识别月份列: {column}")
    return f"{match.group(1)}-{match.group(2)}"


def period_to_date(period: str) -> pd.Timestamp:
    return pd.to_datetime(period + "-01", format="%Y-%m-%d")


def format_period(period: str, include_year: bool = False) -> str:
    date = period_to_date(period)
    return date.strftime("%b %Y" if include_year else "%B")


def resolve_sheet_names(excel: pd.ExcelFile) -> dict[str, str]:
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for key, candidates in SHEET_CANDIDATES.items():
        match = next((name for name in candidates if name in excel.sheet_names), None)
        if match is None:
            missing.append(f"{key}: {', '.join(candidates)}")
        else:
            resolved[key] = match
    if missing:
        raise ValueError("缺少必需工作表或工作表名称已变化：\n" + "\n".join(missing))
    return resolved


def load_name_overrides(path: Path = PRODUCT_OVERRIDES_FILE) -> dict[str, str]:
    if not path.exists():
        return {}
    overrides = pd.read_excel(path) if path.suffix.lower().startswith(".xls") else pd.read_csv(path)
    required = {"ASIN", "display_name"}
    if not required.issubset(overrides.columns):
        return {}
    overrides["ASIN"] = overrides["ASIN"].astype(str).str.strip().str.upper()
    overrides["display_name"] = overrides["display_name"].map(clean_text)
    overrides = overrides.drop_duplicates("ASIN", keep="last")
    return dict(zip(overrides["ASIN"], overrides["display_name"], strict=False))


def _segment_mismatch_count(raw: pd.Series, computed: pd.Series) -> int:
    raw_normalized = raw.astype(str).str.replace("-", "–", regex=False)
    raw_normalized = raw_normalized.replace({"小于2kWh": "<2kWh", "大于5kWh": ">5kWh"})
    valid = raw.notna() & computed.ne(UNKNOWN_SEGMENT)
    return int((raw_normalized[valid] != computed[valid]).sum())


def build_product_master(
    products_raw: pd.DataFrame,
    overrides: dict[str, str],
    brand_colors: dict[str, str],
) -> tuple[pd.DataFrame, int]:
    frame = products_raw.copy()
    frame.columns = [clean_text(column) for column in frame.columns]
    frame["ASIN"] = frame["ASIN"].astype(str).str.strip().str.upper()
    frame["brand_raw"] = frame["品牌"].map(clean_text)
    frame["brand"] = frame["brand_raw"].map(standardize_brand)
    frame["title"] = frame["商品标题"].map(clean_text)
    frame["capacity_wh"] = frame["容量"].map(normalize_capacity_wh)
    frame["capacity_segment"] = frame["capacity_wh"].map(capacity_segment)
    mismatch_count = _segment_mismatch_count(
        frame["容量段"], frame["capacity_segment"]
    )
    frame["series"] = [
        extract_series(title, brand)
        for title, brand in zip(frame["title"], frame["brand"], strict=False)
    ]
    frame["product_name"] = [
        build_product_name(
            brand,
            series,
            capacity,
            title,
            overrides.get(asin, ""),
        )
        for asin, brand, series, capacity, title in zip(
            frame["ASIN"],
            frame["brand"],
            frame["series"],
            frame["capacity_wh"],
            frame["title"],
            strict=False,
        )
    ]
    frame["product_name_short"] = frame["product_name"].map(shorten_product_name)
    frame["product_color"] = [
        product_color(brand, asin, brand_colors)
        for brand, asin in zip(frame["brand"], frame["ASIN"], strict=False)
    ]
    frame = frame.loc[
        ~frame["brand"].str.upper().isin(EXCLUDED_BRANDS)
    ].copy()
    return frame, mismatch_count


def _prepare_history(
    units_raw: pd.DataFrame,
    revenue_raw: pd.DataFrame,
) -> tuple[pd.DataFrame, int, int, int, int]:
    units = units_raw.rename(
        columns={"brand": "brand_raw", "容量段": "source_segment"}
    ).copy()
    revenue = revenue_raw.rename(
        columns={"brand": "brand_raw_revenue", "容量段": "source_segment_revenue"}
    ).copy()
    units["ASIN"] = units["ASIN"].astype(str).str.strip().str.upper()
    revenue["ASIN"] = revenue["ASIN"].astype(str).str.strip().str.upper()

    unit_months = month_columns(units)
    revenue_months = month_columns(revenue)
    units_long = units.melt(
        id_vars=["ASIN", "brand_raw", "source_segment"],
        value_vars=unit_months,
        var_name="source_month",
        value_name="units_raw",
    )
    revenue_long = revenue.melt(
        id_vars=["ASIN", "brand_raw_revenue", "source_segment_revenue"],
        value_vars=revenue_months,
        var_name="source_month",
        value_name="revenue_raw",
    )
    units_long["month"] = units_long["source_month"].map(month_string)
    revenue_long["month"] = revenue_long["source_month"].map(month_string)

    merged = units_long.merge(
        revenue_long,
        on=["ASIN", "month"],
        how="outer",
        validate="one_to_one",
    )
    merged["units_source_present"] = merged["units_raw"].notna()
    merged["revenue_source_present"] = merged["revenue_raw"].notna()
    merged["units"] = pd.to_numeric(merged["units_raw"], errors="coerce")
    merged["revenue"] = pd.to_numeric(merged["revenue_raw"], errors="coerce")
    merged["units"] = merged["units"].where(merged["units_source_present"])
    merged["revenue"] = merged["revenue"].where(
        merged["revenue_source_present"]
    )
    merged["date"] = pd.to_datetime(merged["month"] + "-01")
    merged["year"] = merged["date"].dt.year
    merged["month_number"] = merged["date"].dt.month
    merged["period_label"] = merged["date"].dt.strftime("%b %Y")
    merged["brand_history"] = merged["brand_raw"].map(standardize_brand)
    merged["brand_history_revenue"] = merged["brand_raw_revenue"].map(
        standardize_brand
    )
    merged = merged.loc[merged["year"].isin(ANALYSIS_YEARS)].copy()

    duplicate_count = int(
        merged.duplicated(subset=["ASIN", "month"], keep=False).sum()
    )
    zero_units = int((merged["units"] == 0).sum())
    zero_revenue = int((merged["revenue"] == 0).sum())
    missing_market = int(
        (merged["units"].isna() & merged["revenue"].isna()).sum()
    )
    return merged, duplicate_count, zero_units, zero_revenue, missing_market


def _prepare_prices(
    prices_raw: pd.DataFrame,
    master: pd.DataFrame,
    overrides: dict[str, str],
    brand_colors: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame, int, int]:
    prices = prices_raw.copy()
    prices.columns = [clean_text(column) for column in prices.columns]
    prices["ASIN"] = prices["ASIN"].astype(str).str.strip().str.upper()
    prices["title"] = prices["商品标题"].map(clean_text)
    prices["sku"] = (
        prices["SKU"].map(clean_text)
        if "SKU" in prices.columns
        else ""
    )
    price_months = month_columns(prices)
    long = prices.melt(
        id_vars=["ASIN", "title", "sku"],
        value_vars=price_months,
        var_name="source_month",
        value_name="price_raw",
    )
    long["month"] = long["source_month"].map(month_string)
    long["date"] = pd.to_datetime(long["month"] + "-01")
    long["year"] = long["date"].dt.year
    long = long.loc[long["year"].isin(ANALYSIS_YEARS)].copy()
    long["price_source_present"] = long["price_raw"].notna()
    long["price_numeric"] = pd.to_numeric(long["price_raw"], errors="coerce")
    zero_price_count = int((long["price_numeric"] == 0).sum())
    negative_price_count = int((long["price_numeric"] < 0).sum())
    long["price"] = long["price_numeric"].where(long["price_numeric"] > 0)

    master_columns = [
        "ASIN",
        "brand",
        "capacity_wh",
        "capacity_segment",
        "series",
        "product_name",
        "product_name_short",
        "product_color",
    ]
    long = long.merge(master[master_columns], on="ASIN", how="left")

    missing_meta = long["brand"].isna() | (long["brand"].astype(str) == "")
    if missing_meta.any():
        fallback_rows = long.loc[missing_meta, ["ASIN", "title"]].drop_duplicates(
            "ASIN"
        )
        series_brand_map = (
            master.loc[master["series"].ne("")]
            .drop_duplicates(["series", "brand"])
            .groupby("series")["brand"]
            .agg(list)
        )
        fallback_meta = []
        for row in fallback_rows.itertuples(index=False):
            brand = infer_brand_from_title(row.title)
            capacity = extract_explicit_capacity_wh(row.title)
            segment = capacity_segment(capacity)
            series = extract_series(row.title, brand)
            if not brand and series in series_brand_map.index:
                known_brands = series_brand_map.loc[series]
                if len(known_brands) == 1:
                    brand = known_brands[0]
            name = build_product_name(
                brand,
                series,
                capacity,
                row.title,
                overrides.get(row.ASIN, ""),
            )
            fallback_meta.append(
                {
                    "ASIN": row.ASIN,
                    "brand": brand or "其他品牌",
                    "capacity_wh": capacity,
                    "capacity_segment": segment,
                    "series": series,
                    "product_name": name,
                    "product_name_short": shorten_product_name(name),
                    "product_color": product_color(
                        brand or "其他品牌", row.ASIN, brand_colors
                    ),
                }
            )
        fallback_frame = pd.DataFrame(fallback_meta)
        fallback_lookup = fallback_frame.set_index("ASIN")
        for column in (
            "brand",
            "capacity_wh",
            "capacity_segment",
            "series",
            "product_name",
            "product_name_short",
            "product_color",
        ):
            fill_mask = long[column].isna() | (long[column].astype(str) == "")
            long.loc[fill_mask, column] = long.loc[fill_mask, "ASIN"].map(
                fallback_lookup[column]
            )

    long["period_label"] = long["date"].dt.strftime("%b %Y")
    long["month_number"] = long["date"].dt.month

    catalog = (
        long[
            [
                "ASIN",
                "brand",
                "title",
                "sku",
                "capacity_wh",
                "capacity_segment",
                "series",
                "product_name",
                "product_name_short",
                "product_color",
            ]
        ]
        .drop_duplicates("ASIN")
        .reset_index(drop=True)
    )
    duplicate_names = catalog["product_name_short"].duplicated(keep=False)
    for index in catalog.index[duplicate_names]:
        row = catalog.loc[index]
        hint = extract_variant_hint(row["title"], row["sku"])
        if hint and hint.casefold() not in row["product_name_short"].casefold():
            catalog.loc[index, "product_name_short"] = shorten_product_name(
                f"{row['product_name_short']} · {hint}", max_chars=72
            )
    short_name_map = catalog.set_index("ASIN")["product_name_short"].to_dict()
    long["product_name_short"] = long["ASIN"].map(short_name_map)
    return long, catalog, zero_price_count, negative_price_count


def _pivot_validation(
    excel: pd.ExcelFile,
    market_long: pd.DataFrame,
) -> tuple[int, list[str]]:
    checks = (
        ("按品牌，26月销量", "units", 2026),
        ("按品牌，25月销量", "units", 2025),
        ("按品牌，26月销额", "revenue", 2026),
        ("按品牌，25月销额", "revenue", 2025),
        ("按容量段，26月销量", "units", 2026),
        ("按容量段，25月销量", "units", 2025),
        ("按容量段，26月销额", "revenue", 2026),
        ("按容量段，25月销额", "revenue", 2025),
    )
    mismatches: list[str] = []
    compared = 0
    detail = market_long.copy()
    for sheet, metric, year in checks:
        if sheet not in excel.sheet_names:
            continue
        pivot = pd.read_excel(excel, sheet_name=sheet, header=None)
        if pivot.shape[0] < 3:
            continue
        header_row = 2
        row_labels = pivot.iloc[header_row:, 0].astype(str).str.strip()
        if not (row_labels == "总计").any():
            continue
        total_row = pivot.iloc[header_row:].loc[row_labels == "总计"].iloc[0]
        for column_index, source_total in total_row.items():
            try:
                column_name = pivot.iloc[header_row, column_index]
                pivot_month_name = re.sub(
                    r"^求和项:", "", str(column_name).strip()
                )
                month = month_string(pivot_month_name)
            except ValueError:
                continue
            source_total = pd.to_numeric(source_total, errors="coerce")
            detail_value = detail.loc[
                detail["month"] == month, metric
            ].sum(min_count=1)
            if pd.isna(source_total) and pd.isna(detail_value):
                compared += 1
                continue
            if pd.isna(source_total) != pd.isna(detail_value):
                mismatches.append(
                    f"{sheet} {month}: 汇总页={source_total}, 明细={detail_value}"
                )
                continue
            tolerance = 0.01 if metric == "revenue" else 0
            if abs(float(source_total) - float(detail_value)) > tolerance:
                mismatches.append(
                    f"{sheet} {month}: 汇总页={source_total}, 明细={detail_value}"
                )
            compared += 1
    return compared, mismatches


def load_dashboard_data(source_path: Path | None = None) -> DashboardData:
    path = (source_path or resolve_source_file()).resolve()
    excel = pd.ExcelFile(path, engine="openpyxl")
    sheets = resolve_sheet_names(excel)
    raw = {
        key: pd.read_excel(excel, sheet_name=sheet_name, dtype=object)
        for key, sheet_name in sheets.items()
    }
    brand_colors = brand_color_map(
        raw["products"]["品牌"].map(standardize_brand).dropna().unique().tolist()
        + raw["units"]["brand"].map(standardize_brand).dropna().unique().tolist()
        + raw["prices"]["商品标题"].map(infer_brand_from_title).tolist()
    )
    overrides = load_name_overrides()
    master, segment_mismatches = build_product_master(
        raw["products"], overrides, brand_colors
    )
    market_long, duplicate_count, zero_units, zero_revenue, missing_market = (
        _prepare_history(raw["units"], raw["revenue"])
    )
    market_long = market_long.merge(
        master[
            [
                "ASIN",
                "brand",
                "title",
                "series",
                "capacity_wh",
                "capacity_segment",
                "product_name",
                "product_name_short",
                "product_color",
            ]
        ],
        on="ASIN",
        how="left",
        suffixes=("_history", "_master"),
    )
    master_brand_column = (
        "brand_master" if "brand_master" in market_long.columns else "brand"
    )
    market_long["brand"] = market_long[master_brand_column].fillna(
        market_long["brand_history"]
    )
    master_segment_column = (
        "capacity_segment_master"
        if "capacity_segment_master" in market_long.columns
        else "capacity_segment"
    )
    market_long["capacity_segment"] = market_long[
        master_segment_column
    ].fillna(
        market_long["source_segment"].map(
            lambda value: capacity_segment(normalize_capacity_wh(value))
        )
    )
    market_long = market_long.loc[
        ~market_long["brand"].astype(str).str.upper().isin(EXCLUDED_BRANDS)
    ].copy()

    price_long, price_catalog, zero_price_count, negative_price_count = (
        _prepare_prices(raw["prices"], master, overrides, brand_colors)
    )

    quality_issues: list[QualityIssue] = []
    validation_notes: list[str] = []

    compared, mismatches = _pivot_validation(excel, market_long)
    validation_notes.append(
        f"已完成 {compared} 个聚合页/月份账面值核对。"
    )
    if mismatches:
        quality_issues.append(
            QualityIssue(
                "critical",
                "聚合核对",
                "汇总页与 ASIN 明细存在差异",
                "；".join(mismatches[:8])
                + (" …" if len(mismatches) > 8 else ""),
            )
        )
    else:
        validation_notes.append("品牌/容量段汇总页与 ASIN 明细的重叠期间数据一致。")

    if duplicate_count:
        quality_issues.append(
            QualityIssue(
                "warning",
                "重复键",
                "ASIN × 月份存在重复记录",
                f"发现 {duplicate_count} 行疑似重复键；系统不会自动删除。",
            )
        )
    else:
        validation_notes.append("销量/销额明细中 ASIN × 月份无重复键。")

    if segment_mismatches:
        quality_issues.append(
            QualityIssue(
                "warning",
                "容量口径",
                "原始容量段与按 Wh 重算结果不一致",
                f"共有 {segment_mismatches} 行；看板以标准化容量值和统一边界重算。",
            )
        )

    missing_price_meta = int(
        price_catalog["capacity_segment"].eq(UNKNOWN_SEGMENT).sum()
    )
    if missing_price_meta:
        quality_issues.append(
            QualityIssue(
                "notice",
                "缺失字段",
                "部分价格竞品无法可靠识别容量",
                f"{missing_price_meta} 个价格 ASIN 在容量筛选或每 kWh 价格中标记为“未识别”，未推断补齐。",
            )
        )

    price_only = sorted(set(price_catalog["ASIN"]) - set(master["ASIN"]))
    if price_only:
        quality_issues.append(
            QualityIssue(
                "notice",
                "关联缺口",
                "部分价格历史 ASIN 不在当前产品主表",
                f"{len(price_only)} 个 ASIN 的价格仍保留，品牌、标题和可识别容量来自价格表；未用 ASIN 作为界面展示。",
            )
        )

    no_price_history = sorted(set(master["ASIN"]) - set(price_catalog["ASIN"]))
    if no_price_history:
        quality_issues.append(
            QualityIssue(
                "notice",
                "历史深度",
                "部分当前产品没有历史价格序列",
                f"{len(no_price_history)} 个产品仅能参与产品主表/销量分析，不能绘制真实历史价格折线。",
            )
        )

    no_market_history = sorted(set(master["ASIN"]) - set(market_long["ASIN"]))
    if no_market_history:
        quality_issues.append(
            QualityIssue(
                "notice",
                "历史深度",
                "部分当前产品没有销量/销额历史",
                f"{len(no_market_history)} 个产品不会被计入市场 KPI 或市场份额，当前快照也不替代历史数据。",
            )
        )

    if zero_price_count:
        quality_issues.append(
            QualityIssue(
                "warning",
                "零值口径",
                "价格表中的 0 欧元按缺失处理",
                f"发现 {zero_price_count} 个 0 价格单元格；该值不符合有效售价，已保留缺失状态且不计入均价/最低价/最高价。",
            )
        )
    if negative_price_count:
        quality_issues.append(
            QualityIssue(
                "critical",
                "异常价格",
                "价格表存在负值",
                f"发现 {negative_price_count} 个负值；已作为缺失隔离并需要回到源数据核查。",
            )
        )

    if missing_market:
        number_of_cells = int(
            (
                pd.to_numeric(
                    raw["units"][month_columns(raw["units"])].stack(),
                    errors="coerce",
                ).isna()
            ).sum()
        )
        quality_issues.append(
            QualityIssue(
                "notice",
                "缺失值与零值",
                "历史明细同时包含空白与真实 0",
                f"当前分析期间有 {missing_market} 个 ASIN×月记录销量/销额均缺失；空白不填充为 0，"
                f"数值 0 仍作为真实记录保留（销量 0 记录 {zero_units} 条，销额 0 记录 {zero_revenue} 条）。",
            )
        )

    capacity_outliers = master.loc[master["capacity_wh"] > 20_000]
    if not capacity_outliers.empty:
        examples = "；".join(
            f"{row.brand} {format_capacity(row.capacity_wh)}"
            for row in capacity_outliers.itertuples()
        )
        quality_issues.append(
            QualityIssue(
                "warning",
                "异常容量",
                "容量字段包含超高容量产品",
                f"{len(capacity_outliers)} 个产品容量超过 20kWh（{examples}）。按原始容量参与分段和每 kWh 价格，建议业务复核是否为扩展总容量。",
            )
        )

    brand_title_mismatches = []
    for row in master.itertuples():
        inferred = infer_brand_from_title(row.title)
        if inferred and row.brand and inferred != row.brand:
            brand_title_mismatches.append(f"{row.brand} ↔ 标题 {inferred}")
    if brand_title_mismatches:
        quality_issues.append(
            QualityIssue(
                "notice",
                "品牌一致性",
                "品牌字段与商品标题不一致",
                f"发现 {len(brand_title_mismatches)} 条："
                + "；".join(brand_title_mismatches[:5])
                + "。看板保留品牌字段用于聚合，并在标题中展示原始信息。",
            )
        )

    latest_market_month = (
        market_long.loc[market_long["units"].notna() | market_long["revenue"].notna(), "month"]
        .max()
        if not market_long.empty
        else None
    )
    latest_price_month = (
        price_long.loc[price_long["price"].notna(), "month"].max()
        if not price_long.empty
        else None
    )
    if latest_market_month and latest_market_month < "2026-12":
        validation_notes.append(
            f"源数据最新市场月份为 {latest_market_month}；2026 年图表按 YTD 标注，缺失未来月份不会补零。"
        )

    if not (master["ASIN"].duplicated().any()):
        validation_notes.append("当前产品主表 ASIN 唯一。")

    relevant_brands = set(market_long["brand"].dropna()) | set(
        price_catalog["brand"].dropna()
    )
    brand_colors.update(brand_color_map(relevant_brands))

    excel.close()
    return DashboardData(
        source_path=path,
        source_modified=datetime.fromtimestamp(path.stat().st_mtime),
        market_long=market_long,
        product_master=master,
        product_catalog=price_catalog,
        price_long=price_long,
        quality_issues=quality_issues,
        validation_notes=validation_notes,
        latest_market_month=latest_market_month,
        latest_price_month=latest_price_month,
    )


def selected_periods(years: Iterable[int]) -> list[str]:
    return [
        f"{year}-{month:02d}"
        for year in sorted(set(years))
        for month in range(1, 13)
    ]


def filter_market(
    data: DashboardData,
    years: Iterable[int],
    brands: Iterable[str],
) -> pd.DataFrame:
    years_set = set(years)
    brands_set = set(brands)
    return data.market_long.loc[
        data.market_long["year"].isin(years_set)
        & data.market_long["brand"].isin(brands_set)
    ].copy()


def filter_prices(
    data: DashboardData,
    years: Iterable[int],
    brands: Iterable[str],
    segments: Iterable[str],
) -> pd.DataFrame:
    brands_set = set(brands)
    segments_set = set(segments)
    return data.price_long.loc[
        data.price_long["year"].isin(set(years))
        & data.price_long["brand"].isin(brands_set)
        & data.price_long["capacity_segment"].isin(segments_set)
    ].copy()


def aggregate_monthly(
    frame: pd.DataFrame,
    category_column: str,
    years: Iterable[int],
) -> pd.DataFrame:
    periods = selected_periods(years)
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "month",
                "category",
                "units",
                "revenue",
                "units_source_present",
                "revenue_source_present",
            ]
        )
    frame = frame.copy()
    frame["_category"] = frame[category_column]
    frame["_unit_present"] = frame["units"].notna()
    frame["_revenue_present"] = frame["revenue"].notna()
    grouped = (
        frame.groupby(["month", "_category"], dropna=False)
        .agg(
            units=("units", lambda values: values.sum(min_count=1)),
            revenue=("revenue", lambda values: values.sum(min_count=1)),
            units_source_present=("_unit_present", "max"),
            revenue_source_present=("_revenue_present", "max"),
        )
        .reset_index()
    )
    full_index = pd.MultiIndex.from_product(
        [periods, sorted(frame["_category"].dropna().astype(str).unique())],
        names=["month", "_category"],
    ).to_frame(index=False)
    grouped = full_index.merge(
        grouped, on=["month", "_category"], how="left"
    )
    grouped = grouped.rename(columns={"_category": "category"})
    grouped["period_label"] = grouped["month"].map(
        lambda period: format_period(period, include_year=len(set(years)) > 1)
    )
    grouped["date"] = grouped["month"].map(period_to_date)
    return grouped.sort_values(["date", "category"], kind="stable")


def kpis(frame: pd.DataFrame) -> dict[str, float]:
    units = frame["units"].sum(min_count=1)
    revenue = frame["revenue"].sum(min_count=1)
    asp = revenue / units if pd.notna(units := units) and units > 0 else np.nan
    return {
        "units": units,
        "revenue": revenue,
        "asp": asp,
        "unit_records": int(frame["units"].notna().sum()),
        "revenue_records": int(frame["revenue"].notna().sum()),
        "missing_both": int(
            (frame["units"].isna() & frame["revenue"].isna()).sum()
        ),
    }


def aggregate_share(
    market_long: pd.DataFrame,
    year: int,
    dimension: str,
) -> pd.DataFrame:
    dimension_column = "brand" if dimension == "Brand" else "capacity_segment"
    year_frame = market_long.loc[market_long["year"] == year].copy()
    total_units = year_frame["units"].sum(min_count=1)
    total_revenue = year_frame["revenue"].sum(min_count=1)
    grouped = (
        year_frame.groupby(dimension_column, dropna=False)
        .agg(
            units=("units", lambda values: values.sum(min_count=1)),
            revenue=("revenue", lambda values: values.sum(min_count=1)),
        )
        .reset_index()
    )
    grouped["units_share"] = (
        grouped["units"] / total_units if pd.notna(total_units) and total_units else np.nan
    )
    grouped["revenue_share"] = (
        grouped["revenue"] / total_revenue
        if pd.notna(total_revenue) and total_revenue
        else np.nan
    )
    grouped.attrs["total_units"] = total_units
    grouped.attrs["total_revenue"] = total_revenue
    return grouped


def share_change(
    market_long: pd.DataFrame,
    dimension: str,
    metric: str,
) -> pd.DataFrame:
    dimension_column = "brand" if dimension == "Brand" else "capacity_segment"
    share_column = "units_share" if metric == "Units Share" else "revenue_share"
    year_2025 = aggregate_share(market_long, 2025, dimension)
    year_2026 = aggregate_share(market_long, 2026, dimension)
    merged = year_2025[[dimension_column, share_column]].merge(
        year_2026[[dimension_column, share_column]],
        on=dimension_column,
        how="outer",
        suffixes=("_2025", "_2026"),
    )
    merged["change_pp"] = (
        merged[f"{share_column}_2026"] - merged[f"{share_column}_2025"]
    ) * 100
    merged = merged.loc[merged["change_pp"].notna()].copy()
    merged["sort_value"] = merged["change_pp"].abs()
    return merged.sort_values("sort_value", ascending=False).drop(
        columns="sort_value"
    )


def heatmap_data(
    market_long: pd.DataFrame,
    year: int,
    metric: str,
) -> pd.DataFrame:
    metric_column = "units" if metric == "Units" else "revenue"
    year_frame = market_long.loc[market_long["year"] == year].copy()
    pivot = year_frame.pivot_table(
        index="brand",
        columns="capacity_segment",
        values=metric_column,
        aggfunc=lambda values: values.sum(min_count=1),
        observed=True,
    )
    pivot = pivot.reindex(
        index=sorted(year_frame["brand"].dropna().unique()),
        columns=list(SEGMENT_ORDER),
    )
    return pivot


def price_summary(price_frame: pd.DataFrame) -> pd.DataFrame:
    if price_frame.empty:
        return pd.DataFrame(
            columns=[
                "ASIN",
                "brand",
                "product_name",
                "product_name_short",
                "product_color",
                "capacity_wh",
                "capacity_segment",
                "average_price",
                "minimum_price",
                "maximum_price",
                "latest_price",
                "previous_price",
                "change_pct",
                "latest_price_month",
                "previous_price_month",
                "price_per_kwh",
                "valid_price_count",
            ]
        )

    valid = price_frame.loc[price_frame["price"].notna()].copy()
    if valid.empty:
        return price_summary(pd.DataFrame(columns=price_frame.columns))

    rows: list[dict[str, object]] = []
    for asin, product_prices in valid.groupby("ASIN", sort=False):
        product_prices = product_prices.sort_values("date")
        product = product_prices.iloc[0]
        latest = product_prices.iloc[-1]
        previous_month = latest["date"] - pd.offsets.MonthBegin(1)
        previous_match = product_prices.loc[product_prices["date"] == previous_month]
        previous = previous_match.iloc[0] if not previous_match.empty else None
        previous_price = (
            previous["price"] if previous is not None else np.nan
        )
        latest_price = latest["price"]
        change_pct = (
            (latest_price - previous_price) / previous_price
            if pd.notna(previous_price) and previous_price > 0
            else np.nan
        )
        capacity_kwh = (
            float(product["capacity_wh"]) / 1000
            if pd.notna(product["capacity_wh"]) and product["capacity_wh"] > 0
            else np.nan
        )
        rows.append(
            {
                "ASIN": asin,
                "brand": product["brand"],
                "product_name": product["product_name"],
                "product_name_short": product["product_name_short"],
                "product_color": product["product_color"],
                "capacity_wh": product["capacity_wh"],
                "capacity_segment": product["capacity_segment"],
                "average_price": product_prices["price"].mean(),
                "minimum_price": product_prices["price"].min(),
                "maximum_price": product_prices["price"].max(),
                "latest_price": latest_price,
                "previous_price": previous_price,
                "change_pct": change_pct,
                "latest_price_month": latest["month"],
                "previous_price_month": (
                    previous["month"] if previous is not None else None
                ),
                "price_per_kwh": (
                    latest_price / capacity_kwh
                    if capacity_kwh > 0 and pd.notna(latest_price)
                    else np.nan
                ),
                "valid_price_count": len(product_prices),
            }
        )
    return pd.DataFrame(rows)


def top_price_products(
    price_frame: pd.DataFrame,
    market_long: pd.DataFrame,
    years: Iterable[int],
    limit: int = 8,
) -> list[str]:
    summary = price_summary(price_frame)
    if summary.empty:
        return []
    market = market_long.loc[market_long["year"].isin(set(years))]
    revenue_by_product = (
        market.groupby("ASIN")["revenue"]
        .agg(lambda values: values.sum(min_count=1))
        .rename("period_revenue")
    )
    ranked = summary.merge(
        revenue_by_product, left_on="ASIN", right_index=True, how="left"
    )
    ranked["period_revenue_sort"] = ranked["period_revenue"].fillna(-1)
    ranked = ranked.sort_values(
        ["period_revenue_sort", "valid_price_count", "latest_price"],
        ascending=[False, False, False],
    )
    return ranked.head(limit)["ASIN"].tolist()


def expected_year_label(data: DashboardData, year: int) -> str:
    if year == 2026 and data.latest_market_month:
        latest_date = period_to_date(data.latest_market_month)
        if latest_date.year == 2026 and latest_date.month < 12:
            return f"2026 YTD ({latest_date.strftime('%b')})"
    return str(year)
