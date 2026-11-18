from __future__ import annotations

import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = PROJECT_DIR / "data" / "德国亚马逊.xlsx"
DATA_PATH = Path(
    os.environ.get("BALCONY_DATA_PATH", str(DEFAULT_DATA_PATH))
).expanduser()

APP_TITLE = "德国阳台储能市场数据监测看板"
APP_SUBTITLE = "Germany Balcony Energy Storage Market Dashboard"

REPORT_YEARS = (2025, 2026)
DEFAULT_YEAR = 2026

FOCUS_BRANDS = (
    "Anker",
    "ECOFLOW",
    "Hoymiles",
    "Jackery",
    "MARSTEK",
    "Mentech",
    "Powerness",
    "Solakon",
    "SUNNIVA",
    "TSUN",
    "Zendure",
    "ZINNZGREEN",
)

OTHER_BRAND_LABEL = "Other brands"

BRAND_COLORS = {
    "Anker": "#315B88",
    "ECOFLOW": "#2878D0",
    "MARSTEK": "#47A58A",
    "SUNNIVA": "#E3B65B",
    "Hoymiles": "#6C8EBB",
    "Jackery": "#D39A67",
    "Mentech": "#72AFA0",
    "Powerness": "#78909C",
    "Solakon": "#A67C52",
    "TSUN": "#A89FC9",
    "Zendure": "#C68AA3",
    "ZINNZGREEN": "#96A96D",
    OTHER_BRAND_LABEL: "#B7C0CA",
}

CHART_GROUPED_BRANDS = ("TSUN", "Mentech", "Jackery")

CAPACITY_SEGMENTS = (
    "<2kWh",
    "2-3kWh",
    "3-4kWh",
    "4-5kWh",
    ">5kWh",
)

CAPACITY_COLORS = {
    "<2kWh": "#8BA6C1",
    "2-3kWh": "#4D91C6",
    "3-4kWh": "#47A58A",
    "4-5kWh": "#E3B65B",
    ">5kWh": "#D78379",
}

TARGET_PRICE_ASINS = (
    "B0F66LG385",
    "B0F66P1KYD",
    "B0DC447JCB",
    "B0F66YQJGW",
    "B0DF2GV12G",
    "B0D1XMRC56",
    "B0D1XQ3Z56",
    "B0F5B1T5LK",
    "B0F9F1FPNF",
    "B0FSF5CY18",
    "B0FKGQN57D",
)

MONTH_LABELS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)

SHEET_NAMES = {
    "brand_2026": "按品牌，26月销量",
    "brand_2025": "按品牌，25月销量",
    "capacity_2026": "按容量段，26月销量",
    "capacity_2025": "按容量段，25月销量",
    "units": "产品历史月销量",
    "revenue": "历史月销售额",
    "prices": "历史月价格",
    "product_info": "产品信息",
}

PLOTLY_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "scrollZoom": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "toImageButtonOptions": {
        "format": "png",
        "scale": 2,
    },
}

DASHBOARD_CACHE_VERSION = 2

PRICE_CHANGE_RED = "#D64B4B"
PRICE_CHANGE_GREEN = "#238B57"
PRICE_CHANGE_GREY = "#8B97A6"
SHARE_UP_GREEN = "#2E9D63"
SHARE_DOWN_RED = "#D64B4B"
SHARE_FLAT_GREY = "#8B97A6"

NAVY = "#0B2447"
BLUE = "#1E5AA8"
INK = "#142033"
MUTED = "#667085"
SURFACE = "#FFFFFF"
CANVAS = "#F3F6FA"
GRID = "#E6EBF2"
