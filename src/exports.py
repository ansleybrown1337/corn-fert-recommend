from __future__ import annotations

import json
from io import BytesIO
from typing import Iterable

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .calculations import calculate_soil_nitrate_lb_ac
from .models import FieldResult
from .references import METHODOLOGY_ROWS, REFERENCES


def _result_row(result: FieldResult) -> dict[str, object]:
    field = result.field
    drought = result.drought
    total_other = (
        result.credits.legume_n_lb_ac
        + result.credits.manure_n_lb_ac
        + result.credits.other_n_lb_ac
    )
    direct_soil_input_value = (
        field.direct_soil_no3_n_ppm
        if field.soil_nitrate_input_unit == "ppm"
        else calculate_soil_nitrate_lb_ac(field.direct_soil_no3_n_ppm, 24.0)
    )
    soil_layers_input = []
    for layer in field.soil_layers:
        thickness = layer.lower_depth_in - layer.upper_depth_in
        value = (
            layer.no3_n_ppm
            if field.soil_nitrate_input_unit == "ppm"
            else calculate_soil_nitrate_lb_ac(layer.no3_n_ppm, thickness)
        )
        soil_layers_input.append(
            {
                "upper_depth_in": layer.upper_depth_in,
                "lower_depth_in": layer.lower_depth_in,
                "nitrate_value": value,
                "unit": field.soil_nitrate_input_unit,
            }
        )
    return {
        "field_id": field.field_id,
        "field_name": field.field_name,
        "scenario_description": field.scenario_description,
        "calculation_mode": "standard + experimental drought" if drought else "standard CSU",
        "drought_mode": field.drought_mode,
        "full_yield_goal_bu_ac": field.expected_yield_bu_ac,
        "water_limited_yield_method": field.water_limited_yield_method,
        "yield_reduction_pct": field.yield_reduction_pct,
        "direct_water_limited_yield_bu_ac": field.direct_water_limited_yield_bu_ac,
        "water_limited_yield_bu_ac": drought.water_limited_yield_bu_ac if drought else None,
        "soil_nitrate_method": field.soil_nitrate_method,
        "soil_nitrate_input_unit": field.soil_nitrate_input_unit,
        "direct_soil_nitrate_input_value": direct_soil_input_value,
        "direct_soil_no3_n_ppm": field.direct_soil_no3_n_ppm,
        "soil_layers_input_json": json.dumps(soil_layers_input),
        "soil_layers_json": json.dumps([layer.__dict__ if hasattr(layer, "__dict__") else {"upper_depth_in": layer.upper_depth_in, "lower_depth_in": layer.lower_depth_in, "no3_n_ppm": layer.no3_n_ppm} for layer in field.soil_layers]),
        "soil_no3_n_ppm": result.soil_no3_n_ppm,
        "residual_n_credit_lb_ac": result.credits.residual_soil_n_lb_ac,
        "organic_matter_pct": field.organic_matter_pct,
        "organic_matter_credit_lb_ac": result.credits.organic_matter_n_lb_ac,
        "irrigation_no3_n_ppm": field.irrigation_no3_n_ppm,
        "irrigation_through_tasseling_ac_in": field.irrigation_through_tasseling_ac_in,
        "irrigation_n_credit_lb_ac": result.credits.irrigation_water_n_lb_ac,
        "legume_credit_lb_ac": result.credits.legume_n_lb_ac,
        "manure_credit_lb_ac": result.credits.manure_n_lb_ac,
        "other_n_credit_lb_ac": result.credits.other_n_lb_ac,
        "total_other_n_credits_lb_ac": total_other,
        "total_n_credits_lb_ac": result.credits.total_lb_ac,
        "standard_basal_n_need_lb_ac": result.standard.crop_n_need_lb_ac,
        "standard_unbounded_balance_lb_ac": result.standard.unbounded_balance_lb_ac,
        "standard_fertilizer_recommendation_lb_ac": result.standard.fertilizer_n_lb_ac,
        "donovan_reduction_pct": field.donovan_reduction_pct,
        "yield_adjusted_basal_n_need_lb_ac": drought.yield_adjusted_basal_n_need_lb_ac if drought else None,
        "drought_adjusted_n_target_lb_ac": drought.n_availability_target_lb_ac if drought else None,
        "drought_unbounded_balance_lb_ac": drought.unbounded_balance_lb_ac if drought else None,
        "drought_adjusted_fertilizer_recommendation_lb_ac": drought.fertilizer_n_lb_ac if drought else None,
        "validation_warnings": " | ".join(result.warnings),
    }


def results_to_dataframe(results: Iterable[FieldResult]) -> pd.DataFrame:
    return pd.DataFrame([_result_row(result) for result in results])


def export_results_csv(results: Iterable[FieldResult]) -> bytes:
    return results_to_dataframe(results).to_csv(index=False).encode("utf-8-sig")


def _write_dataframe(workbook: Workbook, title: str, dataframe: pd.DataFrame) -> None:
    worksheet = workbook.create_sheet(title)
    worksheet.sheet_view.showGridLines = False
    worksheet.freeze_panes = "A2"
    header_fill = PatternFill("solid", fgColor="1E4D2B")
    header_font = Font(color="FFFFFF", bold=True)
    for column_index, column_name in enumerate(dataframe.columns, start=1):
        cell = worksheet.cell(row=1, column=column_index, value=column_name)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for row_index, row in enumerate(dataframe.itertuples(index=False, name=None), start=2):
        has_long_text = False
        for column_index, value in enumerate(row, start=1):
            if pd.isna(value):
                value = None
            cell = worksheet.cell(row=row_index, column=column_index, value=value)
            if isinstance(value, float):
                cell.number_format = "0.00"
            if isinstance(value, str) and len(value) > 35:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                has_long_text = True
        if has_long_text:
            worksheet.row_dimensions[row_index].height = 60
    worksheet.auto_filter.ref = worksheet.dimensions
    for column_index, column_name in enumerate(dataframe.columns, start=1):
        values = [str(column_name)] + [str(value) for value in dataframe.iloc[:, column_index - 1].dropna().head(100)]
        width = min(45, max(12, max(map(len, values)) + 2))
        worksheet.column_dimensions[get_column_letter(column_index)].width = width
    worksheet.row_dimensions[1].height = 32


def export_results_excel(results: Iterable[FieldResult]) -> bytes:
    results_list = list(results)
    full = results_to_dataframe(results_list)
    summary_columns = [
        "field_id",
        "field_name",
        "scenario_description",
        "calculation_mode",
        "full_yield_goal_bu_ac",
        "water_limited_yield_bu_ac",
        "standard_basal_n_need_lb_ac",
        "drought_adjusted_n_target_lb_ac",
        "total_n_credits_lb_ac",
        "standard_fertilizer_recommendation_lb_ac",
        "drought_adjusted_fertilizer_recommendation_lb_ac",
    ]
    input_columns = [
        "field_id",
        "field_name",
        "scenario_description",
        "drought_mode",
        "full_yield_goal_bu_ac",
        "water_limited_yield_method",
        "yield_reduction_pct",
        "direct_water_limited_yield_bu_ac",
        "soil_nitrate_method",
        "soil_nitrate_input_unit",
        "direct_soil_nitrate_input_value",
        "direct_soil_no3_n_ppm",
        "soil_layers_input_json",
        "soil_layers_json",
        "soil_no3_n_ppm",
        "organic_matter_pct",
        "irrigation_no3_n_ppm",
        "irrigation_through_tasseling_ac_in",
        "legume_credit_lb_ac",
        "manure_credit_lb_ac",
        "other_n_credit_lb_ac",
        "donovan_reduction_pct",
    ]
    identifiers = ["field_id", "field_name", "scenario_description"]
    balance_columns = identifiers + [
        column for column in full.columns if column not in input_columns and column not in identifiers
    ]

    workbook = Workbook()
    workbook.remove(workbook.active)
    _write_dataframe(workbook, "Summary", full.reindex(columns=summary_columns))
    _write_dataframe(workbook, "Inputs", full.reindex(columns=input_columns))
    _write_dataframe(workbook, "N Balance", full.reindex(columns=balance_columns))

    methodology = workbook.create_sheet("Methodology")
    methodology.sheet_view.showGridLines = False
    methodology.append(["Calculation or assumption", "Equation / interpretation", "Primary source"])
    for row in METHODOLOGY_ROWS:
        methodology.append(row)
    methodology.append([])
    methodology.append(["Reference", "Local file", "External link"])
    for reference in REFERENCES:
        methodology.append([reference.title, reference.local_file, reference.url])
    methodology.append([])
    methodology.append(
        [
            "Limitation",
            "The experimental drought adjustment is a research-informed extrapolation and has not been validated as a CSU fertilizer recommendation algorithm.",
            "",
        ]
    )
    methodology.freeze_panes = "A2"
    methodology.column_dimensions["A"].width = 36
    methodology.column_dimensions["B"].width = 88
    methodology.column_dimensions["C"].width = 50
    for cell in methodology[1]:
        cell.fill = PatternFill("solid", fgColor="1E4D2B")
        cell.font = Font(color="FFFFFF", bold=True)
    for cell in methodology[11]:
        cell.fill = PatternFill("solid", fgColor="1E4D2B")
        cell.font = Font(color="FFFFFF", bold=True)
    for row in methodology.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    for row_index in range(2, methodology.max_row + 1):
        longest = max(len(str(methodology.cell(row_index, column).value or "")) for column in range(1, 4))
        if longest > 100:
            methodology.row_dimensions[row_index].height = 48
        elif longest > 55:
            methodology.row_dimensions[row_index].height = 34

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
