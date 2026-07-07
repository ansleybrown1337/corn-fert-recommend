from __future__ import annotations

from .models import FieldResult


def recommendation_summary(result: FieldResult) -> str:
    credits = result.credits.total_lb_ac
    standard = result.standard
    if result.drought is None:
        text = (
            f"At an expected yield of {result.field.expected_yield_bu_ac:.1f} bu/ac, the CSU "
            f"basal crop N need is {standard.crop_n_need_lb_ac:.1f} lb N/ac. Estimated N credits "
            f"total {credits:.1f} lb N/ac, leaving a standard CSU fertilizer recommendation of "
            f"{standard.fertilizer_n_lb_ac:.1f} lb N/ac."
        )
        if standard.unbounded_balance_lb_ac < 0:
            text += (
                f" Credits exceed the crop N need by {-standard.unbounded_balance_lb_ac:.1f} "
                "lb N/ac. Additional fertilizer N is not recommended by this calculation."
            )
        return text

    drought = result.drought
    text = (
        f"At a water-limited yield goal of {drought.water_limited_yield_bu_ac:.1f} bu/ac, the "
        f"yield-adjusted CSU basal crop N need is {drought.yield_adjusted_basal_n_need_lb_ac:.1f} "
        f"lb N/ac. Applying the experimental {result.field.donovan_reduction_pct:.1f}% reduction "
        f"in optimum total N availability reported by Donovan et al. gives a working N availability "
        f"target of {drought.n_availability_target_lb_ac:.1f} lb N/ac. Estimated N credits total "
        f"{credits:.1f} lb N/ac, leaving an experimental fertilizer recommendation of "
        f"{drought.fertilizer_n_lb_ac:.1f} lb N/ac. The standard CSU calculation at the full-yield "
        f"goal recommends {standard.fertilizer_n_lb_ac:.1f} lb N/ac."
    )
    if drought.unbounded_balance_lb_ac < 0:
        text += (
            f" Estimated availability exceeds the experimental target by "
            f"{-drought.unbounded_balance_lb_ac:.1f} lb N/ac. Additional fertilizer N is not "
            "recommended by this experimental calculation; this does not guarantee crop N sufficiency."
        )
    return text

