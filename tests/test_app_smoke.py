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


def test_editing_duplicated_field_keeps_that_field_active() -> None:
    app_path = Path(__file__).parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=30).run()
    assert not app.exception

    next(button for button in app.button if button.label == "Duplicate field").click().run()
    assert not app.exception
    next(button for button in app.button if button.label == "Duplicate field").click().run()
    assert not app.exception

    active_field = next(radio for radio in app.radio if radio.label == "Active field")
    assert len(active_field.options) == 3
    active_field_id = active_field.value
    soil_nitrate = next(
        number_input
        for number_input in app.number_input
        if number_input.label.startswith("Depth-weighted mean soil NO3-N")
    )
    assert soil_nitrate.key.endswith(active_field_id)

    soil_nitrate.set_value(12.0).run()
    assert not app.exception

    active_field_after_edit = next(radio for radio in app.radio if radio.label == "Active field")
    soil_nitrate_after_edit = next(
        number_input
        for number_input in app.number_input
        if number_input.label.startswith("Depth-weighted mean soil NO3-N")
    )
    assert active_field_after_edit.value == active_field_id
    assert soil_nitrate_after_edit.key.endswith(active_field_id)
    assert soil_nitrate_after_edit.value == 12.0
