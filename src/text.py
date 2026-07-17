from __future__ import annotations

from .models import FieldResult


def recommendation_summary(result: FieldResult) -> str:
    credits = result.credits.total_lb_ac
    standard = result.standard
    if result.drought is None:
        text = (
            f"The standard CSU fertilizer N recommendation is {standard.fertilizer_n_lb_ac:.1f} "
            f"lb N/ac for a full-irrigation expected yield of "
            f"{result.field.expected_yield_bu_ac:.1f} bu/ac. The CSU basal crop N need is "
            f"{standard.crop_n_need_lb_ac:.1f} lb N/ac, and estimated N credits total "
            f"{credits:.1f} lb N/ac."
        )
        if standard.unbounded_balance_lb_ac < 0:
            text += (
                f" Credits exceed the crop N need by {-standard.unbounded_balance_lb_ac:.1f} "
                "lb N/ac. Additional fertilizer N is not recommended by this calculation."
            )
        return text

    drought = result.drought
    text = (
        f"The experimental drought fertilizer N recommendation is {drought.fertilizer_n_lb_ac:.1f} "
        f"lb N/ac, compared with {standard.fertilizer_n_lb_ac:.1f} lb N/ac from the standard CSU "
        f"full-irrigation calculation. The full-irrigation expected yield is "
        f"{result.field.expected_yield_bu_ac:.1f} bu/ac; the water-limited yield shown for this "
        f"scenario is {drought.water_limited_yield_bu_ac:.1f} bu/ac and is reported as context only, "
        "not as the basis for reducing the N target again. The Donovan adjustment applies a "
        f"{result.field.donovan_reduction_pct:.1f}% reduction to the full-yield CSU crop N need of "
        f"{drought.full_yield_basal_n_need_lb_ac:.1f} lb N/ac, giving an experimental total-N "
        f"availability target of {drought.n_availability_target_lb_ac:.1f} lb N/ac. Estimated N "
        f"credits total {credits:.1f} lb N/ac and are subtracted from that target."
    )
    if drought.unbounded_balance_lb_ac < 0:
        text += (
            f" Estimated availability exceeds the experimental target by "
            f"{-drought.unbounded_balance_lb_ac:.1f} lb N/ac. Additional fertilizer N is not "
            "recommended by this experimental calculation; this does not guarantee crop N sufficiency."
        )
    return text
