from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


DASHBOARD_DIR = Path(__file__).resolve().parents[3]
UNIFIED_APP = DASHBOARD_DIR / "app.py"
FRANCE = "France 🇫🇷"
GERMANY = "Germany 🇩🇪"


def test_unified_dashboard_defaults_to_france():
    app = AppTest.from_file(UNIFIED_APP, default_timeout=45).run()
    assert not app.exception
    assert not app.error
    assert app.segmented_control[0].label == "Country"
    assert app.segmented_control[0].value == FRANCE
    assert len(app.get("plotly_chart")) == 7


def test_switch_to_germany_and_back_to_france():
    app = AppTest.from_file(UNIFIED_APP, default_timeout=45).run()
    app.segmented_control[0].set_value(GERMANY)
    app.run()
    assert not app.exception
    assert not app.error
    assert app.segmented_control[0].value == GERMANY
    assert len(app.get("plotly_chart")) == 7
    assert len(app.multiselect) == 6

    app.segmented_control[0].set_value(FRANCE)
    app.run()
    assert not app.exception
    assert not app.error
    assert app.segmented_control[0].value == FRANCE
    assert len(app.get("plotly_chart")) == 7


def test_germany_year_and_brand_filters_rerun_successfully():
    app = AppTest.from_file(UNIFIED_APP, default_timeout=45).run()
    app.segmented_control[0].set_value(GERMANY)
    app.run()
    app.segmented_control[1].set_value("2025")
    app.multiselect[0].set_value(["Anker", "ECOFLOW"])
    app.run()
    assert not app.exception
    assert not app.error
    assert app.multiselect[0].value == ["Anker", "ECOFLOW"]
