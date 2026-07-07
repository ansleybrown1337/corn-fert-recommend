from __future__ import annotations

from src.models import FieldScenario, SoilLayer
from src.validation import (
    find_duplicate_field_names,
    validate_field_scenario,
    validate_soil_layers,
)


def test_valid_full_depth_layers() -> None:
    report = validate_soil_layers([SoilLayer(0, 8, 5), SoilLayer(8, 24, 3)])
    assert report.is_valid


def test_layer_depth_range_overlap_order_gap_and_coverage_errors() -> None:
    bad_range = validate_soil_layers([SoilLayer(0, 0, 5)])
    assert any("greater" in error for error in bad_range.errors)

    overlap = validate_soil_layers([SoilLayer(0, 12, 5), SoilLayer(8, 24, 3)])
    assert any("overlap" in error for error in overlap.errors)

    ordering = validate_soil_layers([SoilLayer(8, 24, 3), SoilLayer(0, 8, 5)])
    assert any("shallowest" in error for error in ordering.errors)

    gap = validate_soil_layers([SoilLayer(0, 8, 5), SoilLayer(10, 24, 3)])
    assert any("gap" in error for error in gap.errors)

    incomplete = validate_soil_layers([SoilLayer(0, 8, 5), SoilLayer(8, 20, 3)])
    assert any("do not end" in error for error in incomplete.errors)


def test_field_validation_rejects_invalid_scientific_inputs() -> None:
    field = FieldScenario(
        field_name="",
        expected_yield_bu_ac=-1,
        direct_soil_no3_n_ppm=-2,
        organic_matter_pct=-0.5,
        irrigation_no3_n_ppm=-1,
        irrigation_through_tasseling_ac_in=-1,
        legume_credit_lb_ac=-1,
        drought_mode=True,
        yield_reduction_pct=100,
        donovan_reduction_pct=-1,
    )
    report = validate_field_scenario(field)
    assert not report.is_valid
    assert len(report.errors) >= 8


def test_duplicate_names_are_warnings_not_field_errors() -> None:
    fields = [FieldScenario(field_name="North Pivot"), FieldScenario(field_name=" north pivot ")]
    assert find_duplicate_field_names(fields) == ("North Pivot",)
    assert validate_field_scenario(fields[0]).is_valid
