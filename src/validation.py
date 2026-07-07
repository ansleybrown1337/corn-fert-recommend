from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from typing import Iterable

from .models import FieldScenario, SoilLayer


@dataclass(frozen=True, slots=True)
class ValidationReport:
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_soil_layers(
    layers: Iterable[SoilLayer], *, require_full_root_zone: bool = True
) -> ValidationReport:
    layer_list = list(layers)
    errors: list[str] = []
    if not layer_list:
        return ValidationReport(errors=("Enter at least one soil layer.",))

    for index, layer in enumerate(layer_list, start=1):
        if layer.upper_depth_in < 0 or layer.lower_depth_in < 0:
            errors.append(f"Layer {index}: depths cannot be negative.")
        if layer.lower_depth_in <= layer.upper_depth_in:
            errors.append(f"Layer {index}: lower depth must be greater than upper depth.")
        if layer.lower_depth_in > 24:
            errors.append(f"Layer {index}: lower depth cannot exceed 24 inches.")
        if layer.no3_n_ppm < 0:
            errors.append(f"Layer {index}: NO3-N concentration cannot be negative.")

    for index, (previous, current) in enumerate(zip(layer_list, layer_list[1:]), start=2):
        if current.upper_depth_in < previous.upper_depth_in:
            errors.append(f"Layer {index}: layers must be entered from shallowest to deepest.")
        if current.upper_depth_in < previous.lower_depth_in:
            errors.append(f"Layer {index}: overlaps the preceding layer.")
        elif current.upper_depth_in > previous.lower_depth_in:
            errors.append(f"Layer {index}: a sampling gap exists before this layer.")

    if require_full_root_zone and layer_list:
        if not isclose(layer_list[0].upper_depth_in, 0.0, abs_tol=1e-9):
            errors.append("Soil layers do not begin at 0 inches; the 0-24 inch root zone is incomplete.")
        if not isclose(layer_list[-1].lower_depth_in, 24.0, abs_tol=1e-9):
            errors.append("Soil layers do not end at 24 inches; the 0-24 inch root zone is incomplete.")

    return ValidationReport(errors=tuple(dict.fromkeys(errors)))


def validate_field_scenario(field: FieldScenario) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []

    if not field.field_name.strip():
        errors.append("Field name cannot be empty.")

    nonnegative_values = {
        "Expected yield": field.expected_yield_bu_ac,
        "Direct soil NO3-N": field.direct_soil_no3_n_ppm,
        "Soil organic matter": field.organic_matter_pct,
        "Irrigation water NO3-N": field.irrigation_no3_n_ppm,
        "Irrigation through tasseling": field.irrigation_through_tasseling_ac_in,
        "Previous crop or legume credit": field.legume_credit_lb_ac,
        "Manure credit": field.manure_credit_lb_ac,
        "Other N credit": field.other_n_credit_lb_ac,
    }
    for label, value in nonnegative_values.items():
        if value < 0:
            errors.append(f"{label} cannot be negative.")

    if field.soil_nitrate_method == "layers":
        report = validate_soil_layers(field.soil_layers, require_full_root_zone=True)
        errors.extend(report.errors)
        warnings.extend(report.warnings)
    elif field.soil_nitrate_method != "direct":
        errors.append("Soil nitrate input method is invalid.")
    if field.soil_nitrate_input_unit not in ("ppm", "lb_ac"):
        errors.append("Soil nitrate input unit is invalid.")

    if field.drought_mode:
        if not 0 <= field.donovan_reduction_pct < 100:
            errors.append("Donovan reduction must be at least 0% and less than 100%.")
        if field.water_limited_yield_method == "percent_reduction":
            if not 0 <= field.yield_reduction_pct < 100:
                errors.append("Yield reduction must be at least 0% and less than 100%.")
        elif field.water_limited_yield_method == "direct":
            if field.direct_water_limited_yield_bu_ac < 0:
                errors.append("Direct water-limited yield cannot be negative.")
            if field.direct_water_limited_yield_bu_ac > field.expected_yield_bu_ac:
                warnings.append("Water-limited yield exceeds the full-irrigation yield goal.")
        else:
            errors.append("Water-limited yield method is invalid.")

    return ValidationReport(
        errors=tuple(dict.fromkeys(errors)), warnings=tuple(dict.fromkeys(warnings))
    )


def find_duplicate_field_names(fields: Iterable[FieldScenario]) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    display: dict[str, str] = {}
    for field in fields:
        normalized = field.field_name.strip().casefold()
        if normalized:
            counts[normalized] = counts.get(normalized, 0) + 1
            display.setdefault(normalized, field.field_name.strip())
    return tuple(display[name] for name, count in counts.items() if count > 1)
