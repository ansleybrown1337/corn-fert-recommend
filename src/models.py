from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal
from uuid import uuid4


SoilNitrateMethod = Literal["direct", "layers"]
SoilNitrateUnit = Literal["ppm", "lb_ac"]
WaterLimitedYieldMethod = Literal["percent_reduction", "direct"]


@dataclass(slots=True)
class SoilLayer:
    upper_depth_in: float
    lower_depth_in: float
    no3_n_ppm: float


@dataclass(slots=True)
class FieldScenario:
    field_id: str = field(default_factory=lambda: str(uuid4()))
    field_name: str = "Field 1"
    scenario_description: str = ""
    expected_yield_bu_ac: float = 200.0
    drought_mode: bool = False
    water_limited_yield_method: WaterLimitedYieldMethod = "percent_reduction"
    yield_reduction_pct: float = 20.0
    direct_water_limited_yield_bu_ac: float = 160.0
    donovan_reduction_pct: float = 31.0
    soil_nitrate_method: SoilNitrateMethod = "direct"
    soil_nitrate_input_unit: SoilNitrateUnit = "ppm"
    direct_soil_no3_n_ppm: float = 5.0
    soil_layers: list[SoilLayer] = field(
        default_factory=lambda: [SoilLayer(0.0, 8.0, 5.0), SoilLayer(8.0, 24.0, 5.0)]
    )
    organic_matter_pct: float = 1.5
    irrigation_no3_n_ppm: float = 0.0
    irrigation_through_tasseling_ac_in: float = 0.0
    legume_credit_lb_ac: float = 0.0
    manure_credit_lb_ac: float = 0.0
    other_n_credit_lb_ac: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NCreditBreakdown:
    residual_soil_n_lb_ac: float
    organic_matter_n_lb_ac: float
    irrigation_water_n_lb_ac: float
    legume_n_lb_ac: float
    manure_n_lb_ac: float
    other_n_lb_ac: float

    @property
    def total_lb_ac(self) -> float:
        return sum(
            (
                self.residual_soil_n_lb_ac,
                self.organic_matter_n_lb_ac,
                self.irrigation_water_n_lb_ac,
                self.legume_n_lb_ac,
                self.manure_n_lb_ac,
                self.other_n_lb_ac,
            )
        )


@dataclass(frozen=True, slots=True)
class StandardRecommendation:
    crop_n_need_lb_ac: float
    unbounded_balance_lb_ac: float
    fertilizer_n_lb_ac: float


@dataclass(frozen=True, slots=True)
class DroughtRecommendation:
    water_limited_yield_bu_ac: float
    yield_adjusted_basal_n_need_lb_ac: float
    n_availability_target_lb_ac: float
    unbounded_balance_lb_ac: float
    fertilizer_n_lb_ac: float


@dataclass(frozen=True, slots=True)
class FieldResult:
    field: FieldScenario
    soil_no3_n_ppm: float
    credits: NCreditBreakdown
    standard: StandardRecommendation
    drought: DroughtRecommendation | None = None
    warnings: tuple[str, ...] = ()
