from __future__ import annotations

from io import BytesIO

from openpyxl import load_workbook

from src.calculations import calculate_batch_scenarios
from src.exports import export_results_csv, export_results_excel, results_to_dataframe
from src.models import FieldScenario


def _results():
    return calculate_batch_scenarios(
        [
            FieldScenario(field_id="a", field_name="A"),
            FieldScenario(field_id="b", field_name="B", drought_mode=True),
            FieldScenario(field_id="c", field_name="C", direct_soil_no3_n_ppm=50),
        ]
    )


def test_summary_dataframe_contains_inputs_intermediates_and_outputs() -> None:
    dataframe = results_to_dataframe(_results())
    required = {
        "field_id",
        "drought_mode",
        "direct_soil_no3_n_ppm",
        "soil_nitrate_input_unit",
        "direct_soil_nitrate_input_value",
        "soil_layers_json",
        "soil_no3_n_ppm",
        "organic_matter_pct",
        "total_n_credits_lb_ac",
        "standard_basal_n_need_lb_ac",
        "standard_unbounded_balance_lb_ac",
        "standard_fertilizer_recommendation_lb_ac",
        "drought_adjusted_n_target_lb_ac",
        "drought_adjusted_fertilizer_recommendation_lb_ac",
    }
    assert required.issubset(dataframe.columns)
    assert len(dataframe) == 3


def test_csv_export_contains_all_records() -> None:
    text = export_results_csv(_results()).decode("utf-8-sig")
    assert "field_id" in text
    assert all(f",{name}," in text for name in ("A", "B", "C"))
    assert len(text.strip().splitlines()) == 4


def test_excel_export_has_expected_sheets_and_formatting() -> None:
    workbook = load_workbook(BytesIO(export_results_excel(_results())), data_only=False)
    assert workbook.sheetnames == ["Summary", "Inputs", "N Balance", "Methodology"]
    assert workbook["Summary"].freeze_panes == "A2"
    assert workbook["Inputs"].max_row == 4
    assert workbook["N Balance"].max_row == 4
    assert workbook["N Balance"]["A1"].value == "field_id"
    assert workbook["N Balance"]["B2"].value == "A"
    assert workbook["Methodology"].max_row > 10
    assert workbook["Summary"]["A1"].font.bold
