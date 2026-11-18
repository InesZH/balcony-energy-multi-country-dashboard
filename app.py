from __future__ import annotations

import runpy
from pathlib import Path

import streamlit as st


PROJECT_DIR = Path(__file__).resolve().parent
FRANCE_DASHBOARD = PROJECT_DIR / "france_dashboard.py"

FRANCE_OPTION = "France 🇫🇷"
GERMANY_OPTION = "Germany 🇩🇪"


st.set_page_config(
    page_title="Multi-Country Balcony Energy Storage Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
)


COUNTRY_SELECTOR_CSS = """
<style>
.country-switcher-title {
    color: #24313a;
    font-size: 13px;
    font-weight: 750;
    letter-spacing: 0.015em;
    margin: 0 0 3px;
}
.country-switcher-note {
    color: #738089;
    font-size: 11px;
    line-height: 1.45;
}
@media (max-width: 900px) {
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 0.65rem !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }
}
</style>
"""


def render_country_selector() -> str:
    st.markdown(COUNTRY_SELECTOR_CSS, unsafe_allow_html=True)
    with st.container(border=True, key="country_selector_container"):
        label_column, selector_column = st.columns(
            [1.15, 4.85], gap="large"
        )
        with label_column:
            st.markdown(
                """
                <div class="country-switcher-title">Country Selector</div>
                <div class="country-switcher-note">
                  两国数据、KPI 与分析逻辑独立
                </div>
                """,
                unsafe_allow_html=True,
            )
        with selector_column:
            selected = st.segmented_control(
                "Country",
                options=[FRANCE_OPTION, GERMANY_OPTION],
                default=FRANCE_OPTION,
                selection_mode="single",
                key="country_selector",
                label_visibility="collapsed",
                width="stretch",
            )
    return selected or FRANCE_OPTION


country = render_country_selector()

if country == GERMANY_OPTION:
    from countries.germany.dashboard import main as render_germany_dashboard

    render_germany_dashboard()
else:
    if not FRANCE_DASHBOARD.exists():
        st.error(f"未找到法国看板脚本：{FRANCE_DASHBOARD}")
        st.stop()
    runpy.run_path(str(FRANCE_DASHBOARD), run_name="france_dashboard")
