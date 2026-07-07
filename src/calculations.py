from __future__ import annotations

from typing import Iterable

from .models import (
    DroughtRecommendation,
    FieldResult,
    FieldScenario,
    NCreditBreakdown,
    SoilLayer,
    StandardRecommendation,
)
from .validation import validate_field_scenario, validate_soil_layers


class CalculationInputError(ValueError):
    """Raised when scientific inputs fail validation."""


def _require_nonnegative(value: float, label: str) -> None:
    if value < 0:
        raise CalculationInputError(f"{label} cannot be negative.")


def _require_reduction(value: float, label: str) -> None:
    if not 0 <= value < 100:
        raise CalculationInputError(f"{label} must be at least 0% and less than 100%.")


def calculate_crop_n_need(expected_yield_bu_ac: float) -> float:
    _require_nonnegative(expected_yield_bu_ac, "Expected yield")
    return 35.0 + 1.2 * expected_yield_bu_ac


def calculate_weighted_soil_nitrate(layers: Iterable[SoilLayer]) -> float:
    layer_list = list(layers)
    report = validate_soil_layers(layer_list, require_full_root_zone=False)
    if report.errors:
        raise CalculationInputError(" ".join(report.errors))
    total_thickness = sum(layer.lower_depth_in - layer.upper_depth_in for layer in layer_list)
    if total_thickness <= 0:
        raise CalculationInputError("Total sampled soil thickness must be positive.")
    return (
        sum(
            (layer.lower_depth_in - layer.upper_depth_in) * layer.no3_n_ppm
            for layer in layer_list
        )
        / total_thickness
    )


def calculate_residual_soil_n_credit(no3_n_ppm: float) -> float:
    _require_nonnegative(no3_n_ppm, "Soil NO3-N")
    return 8.0 * no3_n_ppm


def calculate_soil_nitrate_lb_ac(no3_n_ppm: float, layer_thickness_in: float) -> float:
    """Convert layer NO3-N ppm to lb N/ac using the CSU 0-24 inch factor."""
    _require_nonnegative(no3_n_ppm, "Soil NO3-N")
    if layer_thickness_in <= 0:
        raise CalculationInputError("Soil layer thickness must be positive.")
    return no3_n_ppm * 8.0 * (layer_thickness_in / 24.0)


def calculate_soil_nitrate_ppm(no3_n_lb_ac: float, layer_thickness_in: float) -> float:
    """Convert layer lb N/ac to ppm using the CSU 0-24 inch factor."""
    _require_nonnegative(no3_n_lb_ac, "Soil nitrate N")
    if layer_thickness_in <= 0:
        raise CalculationInputError("Soil layer thickness must be positive.")
    return no3_n_lb_ac / (8.0 * (layer_thickness_in / 24.0))


def calculate_organic_matter_credit(
    expected_yield_bu_ac: float, organic_matter_pct: float
) -> float:
    _require_nonnegative(expected_yield_bu_ac, "Expected yield")
    _require_nonnegative(organic_matter_pct, "Soil organic matter")
    return 0.14 * expected_yield_bu_ac * organic_matter_pct


def calculate_irrigation_n_credit(no3_n_ppm: float, irrigation_ac_in: float) -> float:
    _require_nonnegative(no3_n_ppm, "Irrigation water NO3-N")
    _require_nonnegative(irrigation_ac_in, "Irrigation through tasseling")
    return 0.223 * no3_n_ppm * irrigation_ac_in


def calculate_total_n_credits(*credits_lb_ac: float) -> float:
    for credit in credits_lb_ac:
        _require_nonnegative(credit, "N credit")
    return sum(credits_lb_ac)


def calculate_standard_fertilizer_recommendation(
    crop_n_need_lb_ac: float, total_n_credits_lb_ac: float
) -> tuple[float, float]:
    _require_nonnegative(crop_n_need_lb_ac, "Crop N need")
    _require_nonnegative(total_n_credits_lb_ac, "Total N credits")
    unbounded = crop_n_need_lb_ac - total_n_credits_lb_ac
    return max(0.0, unbounded), unbounded


def calculate_water_limited_yield(full_yield_bu_ac: float, yield_reduction_pct: float) -> float:
    _require_nonnegative(full_yield_bu_ac, "Full-irrigation yield")
    _require_reduction(yield_reduction_pct, "Yield reduction")
    return full_yield_bu_ac * (1.0 - yield_reduction_pct / 100.0)


def calculate_drought_adjusted_n_target(
    basal_n_need_lb_ac: float, reduction_pct: float = 31.0
) -> float:
    _require_nonnegative(basal_n_need_lb_ac, "Yield-adjusted basal N need")
    _require_reduction(reduction_pct, "Donovan reduction")
    return basal_n_need_lb_ac * (1.0 - reduction_pct / 100.0)


def calculate_drought_fertilizer_recommendation(
    drought_adjusted_n_target_lb_ac: float, total_n_credits_lb_ac: float
) -> tuple[float, float]:
    _require_nonnegative(drought_adjusted_n_target_lb_ac, "Drought-adjusted N target")
    _require_nonnegative(total_n_credits_lb_ac, "Total N credits")
    unbounded = drought_adjusted_n_target_lb_ac - total_n_credits_lb_ac
    return max(0.0, unbounded), unbounded


def calculate_field_scenario(field: FieldScenario) -> FieldResult:
    report = validate_field_scenario(field)
    if report.errors:
        raise CalculationInputError(" ".join(report.errors))

    if field.soil_nitrate_method == "layers":
        soil_no3_n_ppm = calculate_weighted_soil_nitrate(field.soil_layers)
    else:
        soil_no3_n_ppm = field.direct_soil_no3_n_ppm

    credits = NCreditBreakdown(
        residual_soil_n_lb_ac=calculate_residual_soil_n_credit(soil_no3_n_ppm),
        organic_matter_n_lb_ac=calculate_organic_matter_credit(
            field.expected_yield_bu_ac, field.organic_matter_pct
        ),
        irrigation_water_n_lb_ac=calculate_irrigation_n_credit(
            field.irrigation_no3_n_ppm, field.irrigation_through_tasseling_ac_in
        ),
        legume_n_lb_ac=field.legume_credit_lb_ac,
        manure_n_lb_ac=field.manure_credit_lb_ac,
        other_n_lb_ac=field.other_n_credit_lb_ac,
    )

    crop_n_need = calculate_crop_n_need(field.expected_yield_bu_ac)
    standard_fertilizer, standard_unbounded = calculate_standard_fertilizer_recommendation(
        crop_n_need, credits.total_lb_ac
    )
    standard = StandardRecommendation(
        crop_n_need_lb_ac=crop_n_need,
        unbounded_balance_lb_ac=standard_unbounded,
        fertilizer_n_lb_ac=standard_fertilizer,
    )

    drought: DroughtRecommendation | None = None
    if field.drought_mode:
        if field.water_limited_yield_method == "direct":
            water_limited_yield = field.direct_water_limited_yield_bu_ac
        else:
            water_limited_yield = calculate_water_limited_yield(
                field.expected_yield_bu_ac, field.yield_reduction_pct
            )
        yield_adjusted_basal = calculate_crop_n_need(water_limited_yield)
        target = calculate_drought_adjusted_n_target(
            yield_adjusted_basal, field.donovan_reduction_pct
        )
        drought_fertilizer, drought_unbounded = calculate_drought_fertilizer_recommendation(
            target, credits.total_lb_ac
        )
        drought = DroughtRecommendation(
            water_limited_yield_bu_ac=water_limited_yield,
            yield_adjusted_basal_n_need_lb_ac=yield_adjusted_basal,
            n_availability_target_lb_ac=target,
            unbounded_balance_lb_ac=drought_unbounded,
            fertilizer_n_lb_ac=drought_fertilizer,
        )

    return FieldResult(
        field=field,
        soil_no3_n_ppm=soil_no3_n_ppm,
        credits=credits,
        standard=standard,
        drought=drought,
        warnings=report.warnings,
    )


def calculate_batch_scenarios(fields: Iterable[FieldScenario]) -> list[FieldResult]:
    return [calculate_field_scenario(field) for field in fields]
