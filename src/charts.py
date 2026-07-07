from __future__ import annotations

from typing import Iterable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .models import FieldResult


SOURCE_COLORS = {
    "Residual soil nitrate": "#4477AA",
    "Soil organic matter": "#228833",
    "Irrigation water": "#66CCEE",
    "Previous crop / legume": "#CCBB44",
    "Manure": "#AA3377",
    "Other credit": "#BBBBBB",
    "Fertilizer required": "#EE7733",
}


def _credit_pairs(result: FieldResult) -> list[tuple[str, float]]:
    c = result.credits
    return [
        ("Residual soil nitrate", c.residual_soil_n_lb_ac),
        ("Soil organic matter", c.organic_matter_n_lb_ac),
        ("Irrigation water", c.irrigation_water_n_lb_ac),
        ("Previous crop / legume", c.legume_n_lb_ac),
        ("Manure", c.manure_n_lb_ac),
        ("Other credit", c.other_n_lb_ac),
    ]


def individual_n_balance_chart(result: FieldResult) -> go.Figure:
    modes = [("Standard CSU", result.standard.fertilizer_n_lb_ac)]
    if result.drought:
        modes.append(("Experimental drought", result.drought.fertilizer_n_lb_ac))

    fig = go.Figure()
    for label, value in _credit_pairs(result):
        fig.add_trace(
            go.Bar(
                name=label,
                y=[mode for mode, _ in modes],
                x=[value] * len(modes),
                orientation="h",
                marker_color=SOURCE_COLORS[label],
                text=[f"{value:.1f}"] * len(modes),
                textposition="inside" if value >= 12 else "none",
                hovertemplate=f"{label}: %{{x:.1f}} lb N/ac<extra></extra>",
            )
        )
    fig.add_trace(
        go.Bar(
            name="Fertilizer required",
            y=[mode for mode, _ in modes],
            x=[value for _, value in modes],
            orientation="h",
            marker_color=SOURCE_COLORS["Fertilizer required"],
            text=[f"{value:.1f}" for _, value in modes],
            textposition="inside",
            hovertemplate="Fertilizer required: %{x:.1f} lb N/ac<extra></extra>",
        )
    )
    fig.add_vline(
        x=result.standard.crop_n_need_lb_ac,
        line_dash="dash",
        line_color="#222222",
        annotation_text="Standard crop N need",
        annotation_position="top right",
    )
    if result.drought:
        fig.add_vline(
            x=result.drought.n_availability_target_lb_ac,
            line_dash="dot",
            line_color="#882255",
            annotation_text="Experimental target",
            annotation_position="bottom right",
        )
    fig.update_layout(
        barmode="stack",
        height=360 if result.drought else 310,
        margin=dict(l=20, r=20, t=45, b=20),
        xaxis_title="Nitrogen availability and fertilizer (lb N/ac)",
        yaxis_title=None,
        legend_title=None,
        hovermode="y unified",
    )
    return fig


def recommendation_comparison_chart(results: Iterable[FieldResult]) -> go.Figure:
    rows: list[dict[str, object]] = []
    for result in results:
        rows.append(
            {
                "Field": result.field.field_name,
                "Calculation": "Standard CSU",
                "Fertilizer N (lb/ac)": result.standard.fertilizer_n_lb_ac,
            }
        )
        if result.drought:
            rows.append(
                {
                    "Field": result.field.field_name,
                    "Calculation": "Experimental drought",
                    "Fertilizer N (lb/ac)": result.drought.fertilizer_n_lb_ac,
                }
            )
    frame = pd.DataFrame(rows)
    fig = px.bar(
        frame,
        y="Field",
        x="Fertilizer N (lb/ac)",
        color="Calculation",
        barmode="group",
        orientation="h",
        text_auto=".1f",
        color_discrete_map={"Standard CSU": "#4477AA", "Experimental drought": "#EE7733"},
    )
    fig.update_layout(
        height=max(330, 90 + 70 * frame["Field"].nunique()),
        margin=dict(l=20, r=20, t=30, b=20),
        legend_title=None,
        yaxis_title=None,
    )
    return fig


def multi_field_sources_chart(results: Iterable[FieldResult]) -> go.Figure:
    results_list = list(results)
    fig = go.Figure()
    for label in SOURCE_COLORS:
        if label == "Fertilizer required":
            values = [result.standard.fertilizer_n_lb_ac for result in results_list]
        else:
            lookup = dict(_credit_pairs(results_list[0])) if results_list else {}
            if label not in lookup:
                continue
            values = [dict(_credit_pairs(result))[label] for result in results_list]
        fig.add_trace(
            go.Bar(
                name=label,
                x=[result.field.field_name for result in results_list],
                y=values,
                marker_color=SOURCE_COLORS[label],
                hovertemplate=f"{label}: %{{y:.1f}} lb N/ac<extra></extra>",
            )
        )
    fig.update_layout(
        barmode="stack",
        height=430,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title=None,
        yaxis_title="Nitrogen (lb N/ac)",
        legend_title=None,
    )
    return fig

