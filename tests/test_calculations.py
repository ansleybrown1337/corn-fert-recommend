from __future__ import annotations

import pytest

from src.calculations import (
    CalculationInputError,
    calculate_batch_scenarios,
    calculate_crop_n_need,
    calculate_drought_adjusted_n_target,
    calculate_drought_fertilizer_recommendation,
    calculate_field_scenario,
    calculate_irrigation_n_credit,
    calculate_organic_matter_credit,
    calculate_residual_soil_n_credit,
    calculate_soil_nitrate_lb_ac,
    calculate_soil_nitrate_ppm,
    calculate_standard_fertilizer_recommendation,
    calculate_total_n_credits,
    calculate_water_limited_yield,
    calculate_weighted_soil_nitrate,
)
from src.exports import export_results_csv, results_to_dataframe
from src.models import FieldScenario, SoilLayer


def test_csu_worked_example() -> None:
    field = FieldScenario(
        field_id="csu-example",
        field_name="CSU example",
        expected_yield_bu_ac=225.0,
        direct_soil_no3_n_ppm=5.0,
        organic_matter_pct=1.0,
        irrigation_no3_n_ppm=5.0,
        irrigation_through_tasseling_ac_in=24.0,
        legume_credit_lb_ac=30.0,
    )
    result = calculate_field_scenario(field)
    assert result.standard.crop_n_need_lb_ac == pytest.approx(305.0)
    assert result.credits.residual_soil_n_lb_ac == pytest.approx(40.0)
    assert result.credits.organic_matter_n_lb_ac == pytest.approx(31.5)
    assert result.credits.legume_n_lb_ac == pytest.approx(30.0)
    assert result.credits.irrigation_water_n_lb_ac == pytest.approx(26.76)
    assert result.standard.fertilizer_n_lb_ac == pytest.approx(176.74)


def test_required_drought_example_exact_values() -> None:
    water_limited_yield = calculate_water_limited_yield(210.0, 20.0)
    basal = calculate_crop_n_need(water_limited_yield)
    target = calculate_drought_adjusted_n_target(basal, 31.0)
    assert water_limited_yield == pytest.approx(168.0)
    assert basal == pytest.approx(236.6)
    assert target == pytest.approx(163.254)


def test_weighted_soil_nitrate_and_credit() -> None:
    layers = [SoilLayer(0, 8, 20), SoilLayer(8, 24, 8)]
    weighted = calculate_weighted_soil_nitrate(layers)
    assert weighted == pytest.approx(12.0)
    assert calculate_residual_soil_n_credit(weighted) == pytest.approx(96.0)


def test_soil_nitrate_ppm_and_lb_ac_depth_conversions() -> None:
    assert calculate_soil_nitrate_lb_ac(5.0, 8.0) == pytest.approx(13.3333333333)
    assert calculate_soil_nitrate_lb_ac(5.0, 16.0) == pytest.approx(26.6666666667)
    assert calculate_soil_nitrate_lb_ac(5.0, 24.0) == pytest.approx(40.0)
    assert calculate_soil_nitrate_ppm(13.3333333333, 8.0) == pytest.approx(5.0)
    assert calculate_soil_nitrate_ppm(26.6666666667, 16.0) == pytest.approx(5.0)
    assert calculate_soil_nitrate_ppm(40.0, 24.0) == pytest.approx(5.0)


def test_individual_credit_and_balance_functions() -> None:
    assert calculate_organic_matter_credit(225, 1.0) == pytest.approx(31.5)
    assert calculate_irrigation_n_credit(5, 24) == pytest.approx(26.76)
    assert calculate_total_n_credits(40, 31.5, 26.76, 30) == pytest.approx(128.26)
    bounded, unbounded = calculate_standard_fertilizer_recommendation(100, 120)
    assert bounded == 0
    assert unbounded == -20
    bounded, unbounded = calculate_drought_fertilizer_recommendation(80, 30)
    assert bounded == 50
    assert unbounded == 50


def test_negative_inputs_raise() -> None:
    with pytest.raises(CalculationInputError):
        calculate_crop_n_need(-1)
    with pytest.raises(CalculationInputError):
        calculate_irrigation_n_credit(-1, 10)
    with pytest.raises(CalculationInputError):
        calculate_water_limited_yield(200, 100)


def test_batch_scenarios_are_independent_and_export_all_rows() -> None:
    standard = FieldScenario(
        field_id="standard",
        field_name="Standard field",
        expected_yield_bu_ac=210,
        organic_matter_pct=1.0,
    )
    drought = FieldScenario(
        field_id="drought",
        field_name="Drought scenario",
        expected_yield_bu_ac=210,
        organic_matter_pct=1.0,
        drought_mode=True,
        yield_reduction_pct=20,
    )
    high_residual = FieldScenario(
        field_id="high-n",
        field_name="High residual nitrate",
        expected_yield_bu_ac=150,
        direct_soil_no3_n_ppm=40,
        organic_matter_pct=0,
    )
    results = calculate_batch_scenarios([standard, drought, high_residual])
    assert [result.field.field_id for result in results] == ["standard", "drought", "high-n"]
    assert [result.field.field_name for result in results] == [
        "Standard field",
        "Drought scenario",
        "High residual nitrate",
    ]
    assert results[0].drought is None
    assert results[1].drought is not None
    assert results[1].drought.water_limited_yield_bu_ac == pytest.approx(168)
    assert results[0].field.expected_yield_bu_ac == 210
    assert results[2].standard.fertilizer_n_lb_ac == 0
    assert results[2].standard.unbounded_balance_lb_ac < 0
    dataframe = results_to_dataframe(results)
    assert len(dataframe) == 3
    assert set(dataframe["field_id"]) == {"standard", "drought", "high-n"}
    csv_bytes = export_results_csv(results)
    assert csv_bytes.decode("utf-8-sig").count("\n") == 4
