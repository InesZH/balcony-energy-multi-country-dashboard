from __future__ import annotations

import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"

DASHBOARD_TITLE = os.getenv(
    "DASHBOARD_TITLE", "法国阳台储能市场数据监测看板"
)
DASHBOARD_SUBTITLE = os.getenv(
    "DASHBOARD_SUBTITLE", "France Balcony Energy Storage Market Dashboard"
)
DATA_SCOPE = "Amazon.fr · France"

COMPARISON_YEARS = (2025, 2026)
ANALYSIS_YEARS = (2025, 2026)
YEAR_OPTIONS = (2026, 2025, "全部年份")

SEGMENT_ORDER = (
    "<2kWh",
    "2–3kWh",
    "3–4kWh",
    "4–5kWh",
    ">5kWh",
)
UNKNOWN_SEGMENT = "未识别"

SEGMENT_COLORS = {
    "<2kWh": "#68A6A6",
    "2–3kWh": "#6D8DC8",
    "3–4kWh": "#8877B7",
    "4–5kWh": "#D29A5B",
    ">5kWh": "#507A69",
    UNKNOWN_SEGMENT: "#A8B0B8",
}

BRAND_COLORS = {
    "Zendure": "#2F6F8F",
    "EcoFlow": "#3F8F7A",
    "Anker": "#5D7FA8",
    "Jackery": "#C58A57",
    "Marstek": "#7B78A8",
    "FOSSiBOT": "#A36D7A",
    "STORCUBE": "#7D8B7A",
    "BigBlue": "#4D93A8",
    "SAMDUO": "#A08752",
}

BRAND_FALLBACK_COLORS = (
    "#537D8D",
    "#7A8E6B",
    "#967B63",
    "#7D7398",
    "#608A91",
    "#9B765D",
    "#6D8791",
    "#8B8B6D",
)

POSITIVE_COLOR = "#4F8A72"
NEGATIVE_COLOR = "#B46A6A"
NEUTRAL_COLOR = "#9AA4AC"

EXCLUDED_BRANDS = {"TSUN", "MENTECH"}

SHEET_CANDIDATES = {
    "units": ("产品历史月销量",),
    "revenue": ("历史月销售额",),
    "products": ("FR-FRsolarstoragesystem(84)",),
    "prices": ("历史月价格",),
}

PRODUCT_OVERRIDES_FILE = DATA_DIR / "product_name_overrides.csv"

SOURCE_FILE_ENV = "DASHBOARD_DATA_FILE"

MONEY_FORMAT = "€{:,.0f}"
MONEY_FORMAT_2 = "€{:,.2f}"


def resolve_source_file() -> Path:
    configured = os.getenv(SOURCE_FILE_ENV)
    if configured:
        configured_path = Path(configured).expanduser()
        if configured_path.is_file():
            return configured_path
        raise FileNotFoundError(
            f"DASHBOARD_DATA_FILE 指向的文件不存在: {configured_path}"
        )

    files = sorted(
        [
            path
            for path in DATA_DIR.glob("*")
            if path.suffix.lower() in {".xlsx", ".xlsm"}
            and not path.name.startswith("~$")
        ],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not files:
        raise FileNotFoundError(
            f"未在 {DATA_DIR} 中找到 Excel 数据文件。请放入 .xlsx 文件或设置 "
            "DASHBOARD_DATA_FILE。"
        )
    return files[0]
