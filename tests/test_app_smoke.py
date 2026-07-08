from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_pages_and_duplicated_fields_render_without_exceptions() -> None:
    app_path = Path(__file__).parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=30).run()
    assert not app.exception
    assert any(
        button.label == "Download PDF report for all fields" for button in app.get("download_button")
    )

    methodology = next(
        button for button in app.button if button.label == "How was this recommendation calculated?"
    )
    methodology.click().run()
    assert not app.exception
    assert app.sidebar.radio[0].value == "Methodology and References"

    app.sidebar.radio[0].set_value("Recommendations").run()
    assert not app.exception

    duplicate = next(button for button in app.button if button.label == "Duplicate field")
    duplicate.click().run()
    assert not app.exception

    app.sidebar.radio[0].set_value("Compare Fields").run()
    assert not app.exception

    app.sidebar.radio[0].set_value("Methodology and References").run()
    assert not app.exception
