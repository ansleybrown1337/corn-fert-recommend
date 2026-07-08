from __future__ import annotations

import pandas as pd
import streamlit as st

from src.calculations import (
    CalculationInputError,
    calculate_field_scenario,
    calculate_soil_nitrate_lb_ac,
    calculate_soil_nitrate_ppm,
)
from src.charts import (
    individual_n_balance_chart,
    multi_field_sources_chart,
    recommendation_comparison_chart,
)
from src.exports import (
    export_results_csv,
    export_results_excel,
    export_results_pdf,
    results_to_dataframe,
)
from src.models import FieldResult, FieldScenario, SoilLayer
from src.references import REFERENCES, SOURCE_MAPPING
from src.state import duplicate_field, move_field, new_field
from src.text import recommendation_summary
from src.validation import find_duplicate_field_names, validate_field_scenario


st.set_page_config(
    page_title="Colorado Corn Nitrogen Planner",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

AUTHOR_WEBSITE = "https://sites.google.com/view/ansleyjbrown"
GITHUB_REPOSITORY = "https://github.com/ansleybrown1337/corn-fert-recommend"
DONOVAN_DOI = "https://doi.org/10.1016/j.agwat.2026.110456"
CSU_LOGO_URL = (
    "https://agsci.colostate.edu/soilcrop/wp-content/uploads/sites/136/2022/02/"
    "CSU_Logo-01-01.png"
)

st.markdown(
    """
    <style>
    :root { --csu-green: #1E4D2B; --csu-gold: #C8C372; }
    .stApp h1, .stApp h2, .stApp h3 { color: var(--csu-green); }
    div[data-testid="stMetric"] { border: 1px solid #D9E2D9; border-radius: 8px; padding: 0.75rem; }
    div[data-testid="stSidebar"] { border-right: 4px solid var(--csu-gold); }
    .method-note { padding: .8rem 1rem; border-left: 5px solid #C8C372; background: #F7F7F2; }
    .recommendation-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; margin: 1rem 0 1.5rem; }
    .recommendation-box { border: 3px solid #1E4D2B; border-radius: 10px; padding: 1rem 1.2rem; background: #EFF6F0; text-align: center; }
    .recommendation-box.experimental { border-color: #8A6D1D; background: #FFF9E6; }
    .recommendation-label { font-size: .95rem; font-weight: 700; text-transform: uppercase; letter-spacing: .03em; color: #26382C; }
    .recommendation-value { font-size: 2.5rem; line-height: 1.1; font-weight: 800; color: #1E4D2B; margin: .35rem 0 .15rem; }
    .recommendation-box.experimental .recommendation-value { color: #6F5413; }
    .recommendation-unit { font-size: 1.05rem; font-weight: 600; color: #374151; }
    .recommendation-note { margin-top: .5rem; font-size: .88rem; color: #4B5563; }
    .author-byline { margin: -.6rem 0 1.1rem; color: #4B5563; font-size: 1rem; }
    .author-byline a { color: #1E4D2B; font-weight: 650; text-decoration: none; }
    .author-byline a:hover { text-decoration: underline; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _initialize_state() -> None:
    if "fields" not in st.session_state:
        st.session_state.fields = [new_field(1)]


def _navigate_to_methodology() -> None:
    st.session_state.navigation = "Methodology and References"


def _calculate_valid_results(
    fields: list[FieldScenario],
) -> tuple[list[FieldResult], list[tuple[str, str]]]:
    results: list[FieldResult] = []
    errors: list[tuple[str, str]] = []
    for field in fields:
        try:
            results.append(calculate_field_scenario(field))
        except CalculationInputError as exc:
            errors.append((field.field_name or "Unnamed field", str(exc)))
    return results, errors


def _field_management_controls(field: FieldScenario, index: int) -> None:
    fields: list[FieldScenario] = st.session_state.fields
    columns = st.columns([1, 1, 1, 1])
    if columns[0].button("Duplicate field", key=f"duplicate_{field.field_id}", width="stretch"):
        fields.insert(index + 1, duplicate_field(field, len(fields)))
        st.rerun()
    if columns[1].button(
        "Remove field",
        key=f"remove_{field.field_id}",
        disabled=len(fields) == 1,
        width="stretch",
    ):
        fields.pop(index)
        st.rerun()
    if columns[2].button(
        "Move left",
        key=f"left_{field.field_id}",
        disabled=index == 0,
        width="stretch",
    ):
        move_field(fields, index, -1)
        st.rerun()
    if columns[3].button(
        "Move right",
        key=f"right_{field.field_id}",
        disabled=index == len(fields) - 1,
        width="stretch",
    ):
        move_field(fields, index, 1)
        st.rerun()


def _render_field_inputs(field: FieldScenario, index: int) -> list[str]:
    input_errors: list[str] = []
    _field_management_controls(field, index)

    field.field_name = st.text_input(
        "Field name",
        value=field.field_name,
        key=f"name_{field.field_id}",
        help="Enter a physical field, plot, or scenario name. Names need not be unique, but unique names make exports clearer.",
    )
    field.scenario_description = st.text_area(
        "Optional field or scenario description",
        value=field.scenario_description,
        key=f"description_{field.field_id}",
        height=70,
        help="Optionally record management details that distinguish this field or scenario.",
    )

    st.subheader(
        "1. Crop and yield",
        help="Enter a realistic full-irrigation grain-yield goal. Enable the experimental drought adjustment only for water-limited scenario analysis.",
    )
    crop_left, crop_right = st.columns(2)
    field.expected_yield_bu_ac = crop_left.number_input(
        "Full-irrigation expected grain yield (bu/ac)",
        min_value=0.0,
        value=float(field.expected_yield_bu_ac),
        step=1.0,
        key=f"yield_{field.field_id}",
        help="Expected grain yield under full irrigation, in bushels per acre. CSU recommends using a realistic field-specific yield goal.",
    )
    field.drought_mode = crop_right.checkbox(
        "Experimental drought adjustment",
        value=field.drought_mode,
        key=f"drought_{field.field_id}",
        help="Research-informed extrapolation; not an official CSU fertilizer recommendation.",
    )
    if field.drought_mode:
        st.warning(
            "Experimental: combines the CSU yield-based framework with a published water x nitrogen "
            "response. It is not a validated CSU drought recommendation algorithm."
        )
        st.markdown(
            f"**Research basis:** [Donovan et al. (2026)]({DONOVAN_DOI}) reported that maximum "
            "grain yield under limited water occurred with, on average, 31% lower optimum total N "
            "availability than under full water. The yield-loss percentage below remains a user-entered "
            "planning assumption, not a universal value from that study."
        )
        method_label = st.radio(
            "Water-limited yield setup",
            ["Full yield plus reduction", "Direct water-limited yield"],
            index=0 if field.water_limited_yield_method == "percent_reduction" else 1,
            horizontal=True,
            key=f"yield_method_{field.field_id}",
            help="Choose whether to calculate water-limited yield from an editable percentage loss or enter the yield goal directly. The subsequent 31% total-N adjustment is credited to Donovan et al. (2026).",
        )
        field.water_limited_yield_method = (
            "percent_reduction" if method_label == "Full yield plus reduction" else "direct"
        )
        if field.water_limited_yield_method == "percent_reduction":
            field.yield_reduction_pct = st.number_input(
                "Expected yield reduction (%) - editable planning assumption",
                min_value=0.0,
                max_value=99.9,
                value=float(field.yield_reduction_pct),
                step=1.0,
                key=f"yield_reduction_{field.field_id}",
                help=(
                    "The 20% default is a scenario assumption. Local research shows yield response "
                    "varies with stress timing, severity, and year."
                ),
            )
            limited_yield = field.expected_yield_bu_ac * (1 - field.yield_reduction_pct / 100)
            st.info(f"Calculated water-limited yield goal: {limited_yield:.1f} bu/ac")
        else:
            field.direct_water_limited_yield_bu_ac = st.number_input(
                "Water-limited yield goal (bu/ac)",
                min_value=0.0,
                value=float(field.direct_water_limited_yield_bu_ac),
                step=1.0,
                key=f"direct_limited_yield_{field.field_id}",
                help="Enter the expected grain yield directly for this water-limited scenario.",
            )

    st.subheader(
        "2. Soil nitrate",
        help="Enter residual soil nitrate for the full 0-24 inch root-zone sample. Use either a direct weighted value or contiguous sampled layers.",
    )
    nitrate_label = st.radio(
        "Input method",
        ["Direct 0-24 inch weighted mean", "Enter sampled layers"],
        index=0 if field.soil_nitrate_method == "direct" else 1,
        horizontal=True,
        key=f"nitrate_method_{field.field_id}",
        help="Use direct entry if your laboratory already reports a 0-24 inch weighted value. Use layers when surface and subsoil samples are reported separately.",
    )
    field.soil_nitrate_method = "direct" if nitrate_label.startswith("Direct") else "layers"
    previous_unit = field.soil_nitrate_input_unit
    unit_label = st.radio(
        "Soil nitrate units",
        ["ppm NO3-N", "lb nitrate-N/ac"],
        index=0 if previous_unit == "ppm" else 1,
        horizontal=True,
        key=f"nitrate_unit_{field.field_id}",
        help="Select the units shown on the soil report. The app converts lb nitrate-N/ac and ppm using the sampled thickness.",
    )
    selected_unit = "ppm" if unit_label.startswith("ppm") else "lb_ac"
    direct_value_key = f"soil_no3_value_{field.field_id}"
    layer_editor_key = f"layers_{field.field_id}"
    if selected_unit != previous_unit:
        st.session_state[direct_value_key] = (
            field.direct_soil_no3_n_ppm
            if selected_unit == "ppm"
            else calculate_soil_nitrate_lb_ac(field.direct_soil_no3_n_ppm, 24.0)
        )
        st.session_state.pop(layer_editor_key, None)
    field.soil_nitrate_input_unit = selected_unit

    if field.soil_nitrate_method == "direct":
        direct_value = st.number_input(
            (
                "Depth-weighted mean soil NO3-N, 0-24 inches (ppm)"
                if selected_unit == "ppm"
                else "Residual nitrate-N in the 0-24 inch sample (lb N/ac)"
            ),
            min_value=0.0,
            value=float(
                field.direct_soil_no3_n_ppm
                if selected_unit == "ppm"
                else calculate_soil_nitrate_lb_ac(field.direct_soil_no3_n_ppm, 24.0)
            ),
            step=0.1,
            key=direct_value_key,
            help="Enter the laboratory result for the combined 0-24 inch sample in the selected units.",
        )
        field.direct_soil_no3_n_ppm = (
            float(direct_value)
            if selected_unit == "ppm"
            else calculate_soil_nitrate_ppm(float(direct_value), 24.0)
        )
        if selected_unit == "ppm":
            st.caption(
                f"Equivalent residual nitrate credit: "
                f"{calculate_soil_nitrate_lb_ac(field.direct_soil_no3_n_ppm, 24.0):.1f} lb N/ac."
            )
        else:
            st.caption(
                f"Equivalent 0-24 inch concentration: {field.direct_soil_no3_n_ppm:.2f} ppm NO3-N. "
                "For a 0-24 inch bulk sample, ppm = lb N/ac / 8."
            )
    else:
        nitrate_column = "NO3-N (ppm)" if selected_unit == "ppm" else "Nitrate-N (lb N/ac in layer)"
        layer_frame = pd.DataFrame(
            [
                {
                    "Upper depth (in)": layer.upper_depth_in,
                    "Lower depth (in)": layer.lower_depth_in,
                    nitrate_column: (
                        layer.no3_n_ppm
                        if selected_unit == "ppm"
                        else calculate_soil_nitrate_lb_ac(
                            layer.no3_n_ppm, layer.lower_depth_in - layer.upper_depth_in
                        )
                    ),
                }
                for layer in field.soil_layers
            ]
        )
        edited = st.data_editor(
            layer_frame,
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            key=layer_editor_key,
            column_config={
                "Upper depth (in)": st.column_config.NumberColumn(min_value=0.0, max_value=24.0),
                "Lower depth (in)": st.column_config.NumberColumn(min_value=0.0, max_value=24.0),
                nitrate_column: st.column_config.NumberColumn(min_value=0.0, format="%.2f"),
            },
        )
        parsed_layers: list[SoilLayer] = []
        for row_index, row in edited.iterrows():
            if row.isna().all():
                continue
            if row.isna().any():
                input_errors.append(f"Soil layer row {row_index + 1} is incomplete.")
                continue
            upper_depth = float(row["Upper depth (in)"])
            lower_depth = float(row["Lower depth (in)"])
            nitrate_value = float(row[nitrate_column])
            thickness = lower_depth - upper_depth
            no3_n_ppm = (
                nitrate_value
                if selected_unit == "ppm" or thickness <= 0
                else calculate_soil_nitrate_ppm(nitrate_value, thickness)
            )
            parsed_layers.append(
                SoilLayer(
                    upper_depth_in=upper_depth,
                    lower_depth_in=lower_depth,
                    no3_n_ppm=no3_n_ppm,
                )
            )
        field.soil_layers = parsed_layers
        st.caption(
            "Layers must be ordered, contiguous, non-overlapping, and cover the full 0-24 inch interval. "
            "The app does not extrapolate through gaps or unsampled depth."
        )
        if selected_unit == "lb_ac":
            st.caption(
                "Layer conversions derived from CSU's 8 lb N/ac per ppm over 24 inches: "
                "ppm = lb N/ac / 2.667 for 0-8 inches, and ppm = lb N/ac / 5.333 for 8-24 inches."
            )

    st.subheader(
        "3. Soil organic matter",
        help="Use the percent organic matter reported for the surface 0-8 inch soil sample.",
    )
    field.organic_matter_pct = st.number_input(
        "Soil organic matter, 0-8 inches (%)",
        min_value=0.0,
        value=float(field.organic_matter_pct),
        step=0.1,
        key=f"om_{field.field_id}",
        help="Enter soil organic matter as a percentage, typically from the 0-8 inch sample.",
    )

    st.subheader(
        "4. Irrigation water",
        help="Enter irrigation-water nitrate concentration and water expected to be applied from planting through tasseling only.",
    )
    water_left, water_right = st.columns(2)
    field.irrigation_no3_n_ppm = water_left.number_input(
        "Irrigation water NO3-N (ppm)",
        min_value=0.0,
        value=float(field.irrigation_no3_n_ppm),
        step=0.1,
        key=f"water_no3_{field.field_id}",
        help="Enter laboratory-reported irrigation-water nitrate as NO3-N in ppm, not nitrate (NO3) in ppm.",
    )
    field.irrigation_through_tasseling_ac_in = water_right.number_input(
        "Irrigation applied through tasseling (acre-inches)",
        min_value=0.0,
        value=float(field.irrigation_through_tasseling_ac_in),
        step=0.5,
        key=f"irrigation_{field.field_id}",
        help="For the CSU N credit, count irrigation water applied from planting through tasseling.",
    )

    st.subheader(
        "5. Other N credits",
        help="Enter independently estimated N credits from the previous crop, manure, or another documented source. Do not duplicate soil or irrigation credits.",
    )
    credit_columns = st.columns(3)
    field.legume_credit_lb_ac = credit_columns[0].number_input(
        "Previous crop / legume (lb N/ac)",
        min_value=0.0,
        value=float(field.legume_credit_lb_ac),
        step=1.0,
        key=f"legume_{field.field_id}",
        help="Enter the applicable previous-crop or legume N credit in lb N/ac using current local guidance.",
    )
    field.manure_credit_lb_ac = credit_columns[1].number_input(
        "Manure (lb N/ac)",
        min_value=0.0,
        value=float(field.manure_credit_lb_ac),
        step=1.0,
        key=f"manure_{field.field_id}",
        help="Enter the estimated plant-available manure N credit in lb N/ac, accounting for analysis, application, and year since application.",
    )
    field.other_n_credit_lb_ac = credit_columns[2].number_input(
        "Other user-defined credit (lb N/ac)",
        min_value=0.0,
        value=float(field.other_n_credit_lb_ac),
        step=1.0,
        key=f"other_credit_{field.field_id}",
        help="Enter any additional documented N credit in lb N/ac that is not already represented elsewhere.",
    )

    if field.drought_mode:
        with st.expander("6. Advanced drought assumptions"):
            field.donovan_reduction_pct = st.number_input(
                "Reduction in optimum total N availability (%)",
                min_value=0.0,
                max_value=99.9,
                value=float(field.donovan_reduction_pct),
                step=1.0,
                key=f"donovan_{field.field_id}",
                help="Default 31% from Donovan et al. (2026). This concerns total N availability, not fertilizer alone.",
            )
            st.caption(
                "Method choice: the reduction is applied to the yield-adjusted CSU basal crop N need. "
                "The same CSU credits calculated for the full-yield standard reference are then subtracted."
            )
    return input_errors


def _render_field_result(field: FieldScenario, input_errors: list[str]) -> None:
    report = validate_field_scenario(field)
    errors = list(report.errors) + input_errors
    if errors:
        st.error("Recommendation unavailable until these inputs are corrected:")
        for error in dict.fromkeys(errors):
            st.write(f"- {error}")
        return
    for warning in report.warnings:
        st.warning(warning)

    result = calculate_field_scenario(field)
    st.divider()
    st.subheader("Recommendation results")
    if result.drought:
        first = st.columns(5)
        first[0].metric("Full yield goal", f"{field.expected_yield_bu_ac:.0f} bu/ac")
        first[1].metric("Water-limited yield", f"{result.drought.water_limited_yield_bu_ac:.1f} bu/ac")
        first[2].metric("Standard crop N need", f"{result.standard.crop_n_need_lb_ac:.1f} lb/ac")
        first[3].metric("Standard CSU fertilizer N", f"{result.standard.fertilizer_n_lb_ac:.1f} lb/ac")
        first[4].metric("Total N credits", f"{result.credits.total_lb_ac:.1f} lb/ac")
        second = st.columns(3)
        second[0].metric(
            "Yield-adjusted basal N need",
            f"{result.drought.yield_adjusted_basal_n_need_lb_ac:.1f} lb/ac",
        )
        second[1].metric(
            "Experimental drought-adjusted N availability target",
            f"{result.drought.n_availability_target_lb_ac:.1f} lb/ac",
        )
        second[2].metric(
            "Experimental fertilizer N",
            f"{result.drought.fertilizer_n_lb_ac:.1f} lb/ac",
        )
    else:
        metrics = st.columns(4)
        metrics[0].metric("Expected yield", f"{field.expected_yield_bu_ac:.0f} bu/ac")
        metrics[1].metric("Basal crop N need", f"{result.standard.crop_n_need_lb_ac:.1f} lb/ac")
        metrics[2].metric("Total N credits", f"{result.credits.total_lb_ac:.1f} lb/ac")
        metrics[3].metric("Recommended fertilizer N", f"{result.standard.fertilizer_n_lb_ac:.1f} lb/ac")

    if result.drought:
        st.markdown(
            f"""
            <div class="recommendation-grid">
              <div class="recommendation-box">
                <div class="recommendation-label">Standard CSU fertilizer N recommendation</div>
                <div class="recommendation-value">{result.standard.fertilizer_n_lb_ac:.1f}</div>
                <div class="recommendation-unit">lb N/ac</div>
                <div class="recommendation-note">Reference calculation after all entered N credits</div>
              </div>
              <div class="recommendation-box experimental">
                <div class="recommendation-label">Experimental drought-adjusted fertilizer N</div>
                <div class="recommendation-value">{result.drought.fertilizer_n_lb_ac:.1f}</div>
                <div class="recommendation-unit">lb N/ac</div>
                <div class="recommendation-note">Research-informed extrapolation; not an official CSU recommendation</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="recommendation-grid">
              <div class="recommendation-box">
                <div class="recommendation-label">Calculated fertilizer N recommendation</div>
                <div class="recommendation-value">{result.standard.fertilizer_n_lb_ac:.1f}</div>
                <div class="recommendation-unit">lb N/ac</div>
                <div class="recommendation-note">Standard CSU calculation after all entered N credits</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.plotly_chart(
        individual_n_balance_chart(result),
        key=f"balance_chart_{field.field_id}",
        width="stretch",
    )
    st.markdown(f"**Interpretation.** {recommendation_summary(result)}")
    st.button(
        "How was this recommendation calculated?",
        key=f"methodology_{field.field_id}",
        on_click=_navigate_to_methodology,
    )
    with st.expander("Calculation detail and unbounded balances"):
        detail = pd.DataFrame(
            {
                "Component": [
                    "Residual soil nitrate",
                    "Soil organic matter",
                    "Irrigation water",
                    "Previous crop / legume",
                    "Manure",
                    "Other credit",
                    "Total credits",
                    "Standard unbounded balance",
                    "Experimental unbounded balance",
                ],
                "lb N/ac": [
                    result.credits.residual_soil_n_lb_ac,
                    result.credits.organic_matter_n_lb_ac,
                    result.credits.irrigation_water_n_lb_ac,
                    result.credits.legume_n_lb_ac,
                    result.credits.manure_n_lb_ac,
                    result.credits.other_n_lb_ac,
                    result.credits.total_lb_ac,
                    result.standard.unbounded_balance_lb_ac,
                    result.drought.unbounded_balance_lb_ac if result.drought else None,
                ],
            }
        )
        st.dataframe(
            detail,
            key=f"detail_table_{field.field_id}",
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "A negative unbounded balance means estimated credits exceed the relevant calculated target. "
            "The displayed fertilizer recommendation is bounded at zero."
        )


def recommendations_page() -> None:
    st.title("Colorado Corn Nitrogen Planner")
    st.markdown(
        f"""
        <div class="author-byline">
          Created by <a href="{AUTHOR_WEBSITE}" target="_blank">AJ Brown</a>, Agricultural Data Scientist
          &nbsp;·&nbsp; <a href="{GITHUB_REPOSITORY}" target="_blank">View project on GitHub</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write(
        "Standard CSU irrigated grain-corn nitrogen recommendations with an optional, clearly "
        "separated experimental drought scenario. A field can represent a physical field, plot, or hypothetical scenario."
    )
    if st.button("Add another field", type="primary", width="content"):
        st.session_state.fields.append(new_field(len(st.session_state.fields) + 1))
        st.rerun()

    fields: list[FieldScenario] = st.session_state.fields
    duplicate_names = find_duplicate_field_names(fields)
    if duplicate_names:
        st.warning(
            "Duplicate field names may make comparisons and exports ambiguous: " + ", ".join(duplicate_names)
        )

    tabs = st.tabs(
        [f"{field.field_name.strip() or 'Unnamed field'} · {index + 1}" for index, field in enumerate(fields)]
    )
    has_input_errors = False
    for index, (tab, field) in enumerate(zip(tabs, fields)):
        with tab:
            input_errors = _render_field_inputs(field, index)
            has_input_errors = has_input_errors or bool(input_errors)
            _render_field_result(field, input_errors)

    batch_results, batch_errors = _calculate_valid_results(fields)
    complete_batch = (
        not has_input_errors and not batch_errors and len(batch_results) == len(fields)
    )
    st.divider()
    st.subheader("Export batch report")
    st.caption(
        "The printable PDF includes every field currently in the batch, with user inputs, "
        "intermediate calculations, recommendations, methodology, and references."
    )
    st.download_button(
        "Download PDF report for all fields",
        data=export_results_pdf(batch_results) if complete_batch else b"",
        file_name="corn_n_recommendations_report.pdf",
        mime="application/pdf",
        disabled=not complete_batch,
        type="primary",
    )
    if not complete_batch:
        st.caption("Correct all field input errors before exporting so no field is omitted from the report.")


def compare_page() -> None:
    st.title("Compare Fields")
    fields: list[FieldScenario] = st.session_state.fields
    duplicates = find_duplicate_field_names(fields)
    if duplicates:
        st.warning("Duplicate field names may make exported records ambiguous: " + ", ".join(duplicates))
    results, errors = _calculate_valid_results(fields)
    for name, error in errors:
        st.error(f"{name}: {error}")
    if not results:
        st.info("No valid field results are available. Correct inputs on the Recommendations page.")
        return

    frame = results_to_dataframe(results)
    display_columns = {
        "field_name": "Field",
        "scenario_description": "Scenario description",
        "calculation_mode": "Mode",
        "full_yield_goal_bu_ac": "Full yield (bu/ac)",
        "water_limited_yield_bu_ac": "Water-limited yield (bu/ac)",
        "standard_basal_n_need_lb_ac": "Basal crop N need (lb/ac)",
        "drought_adjusted_n_target_lb_ac": "Experimental N target (lb/ac)",
        "residual_n_credit_lb_ac": "Residual soil N (lb/ac)",
        "organic_matter_credit_lb_ac": "Organic matter N (lb/ac)",
        "irrigation_n_credit_lb_ac": "Irrigation N (lb/ac)",
        "total_other_n_credits_lb_ac": "Other credits (lb/ac)",
        "total_n_credits_lb_ac": "Total credits (lb/ac)",
        "standard_fertilizer_recommendation_lb_ac": "Standard CSU fertilizer N (lb/ac)",
        "drought_adjusted_fertilizer_recommendation_lb_ac": "Experimental fertilizer N (lb/ac)",
    }
    st.subheader("Field comparison")
    st.dataframe(
        frame[list(display_columns)].rename(columns=display_columns),
        hide_index=True,
        width="stretch",
        column_config={column: st.column_config.NumberColumn(format="%.1f") for column in display_columns.values() if "(lb/ac)" in column or "(bu/ac)" in column},
    )
    st.subheader("Fertilizer recommendation comparison")
    st.plotly_chart(recommendation_comparison_chart(results), width="stretch")
    st.subheader("N sources and standard fertilizer requirement")
    st.plotly_chart(multi_field_sources_chart(results), width="stretch")

    st.subheader("Download reproducible results")
    st.caption("Both exports contain inputs, intermediate values, unbounded balances, and final recommendations.")
    download_columns = st.columns(3)
    download_columns[0].download_button(
        "Download CSV summary",
        data=export_results_csv(results),
        file_name="corn_n_recommendations.csv",
        mime="text/csv",
        width="stretch",
    )
    download_columns[1].download_button(
        "Download detailed Excel workbook",
        data=export_results_excel(results),
        file_name="corn_n_recommendations.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
    complete_batch = not errors and len(results) == len(fields)
    download_columns[2].download_button(
        "Download printable PDF report",
        data=export_results_pdf(results) if complete_batch else b"",
        file_name="corn_n_recommendations_report.pdf",
        mime="application/pdf",
        disabled=not complete_batch,
        width="stretch",
    )
    if not complete_batch:
        st.caption("The PDF requires every field to be valid so the report cannot silently omit a field.")


def methodology_page() -> None:
    st.title("Methodology and References")
    st.markdown(
        '<div class="method-note"><strong>Scope:</strong> This tool estimates fertilizer N for irrigated grain corn. '
        "Crop N need, estimated N availability, fertilizer N, and plant N uptake are distinct quantities.</div>",
        unsafe_allow_html=True,
    )
    st.subheader("Standard CSU calculation")
    st.latex(r"\mathrm{Crop\ N\ need}=35+1.2\times\mathrm{expected\ yield}")
    st.latex(r"\mathrm{Residual\ soil\ N}=8\times\mathrm{weighted\ mean\ NO_3-N\ (ppm)}")
    st.latex(r"\mathrm{OM\ credit}=0.14\times\mathrm{yield}\times\mathrm{OM\ (percent)}")
    st.latex(r"\mathrm{Irrigation\ N}=0.223\times\mathrm{water\ NO_3-N}\times\mathrm{acre\ inches}")
    st.latex(r"\mathrm{Fertilizer\ N}=\max(0,\mathrm{crop\ N\ need}-\mathrm{all\ credits})")
    st.write(
        "The unbounded balance is retained in results and exports so excess estimated credits remain visible. "
        "Soil-layer calculations require contiguous coverage from 0 to 24 inches; missing depth is not extrapolated. "
        "The irrigation-water credit uses water expected to be applied from planting through tasseling."
    )

    st.subheader("Experimental drought adjustment")
    st.write(
        "The tool first establishes a water-limited yield goal, applies the CSU basal equation at that yield, "
        "then reduces that yield-adjusted basal target by the visible Donovan percentage. The standard CSU "
        "credits are subtracted only after this reduction. The standard CSU result remains visible alongside it."
    )
    st.latex(r"Y_w=Y_f\times(1-r_y/100)")
    st.latex(r"T_d=(35+1.2Y_w)\times(1-r_N/100)")
    st.latex(r"F_d=\max(0,T_d-\mathrm{all\ standard\ CSU\ credits})")
    st.warning(
        "The experimental drought adjustment is a research-informed extrapolation and has not been "
        "validated as a CSU fertilizer recommendation algorithm."
    )
    st.write(
        "Donovan et al. evaluated total N availability, including fertilizer, residual soil inorganic N, and "
        "irrigation-water N. Therefore, 31% is not described or applied as a fertilizer-only reduction. "
        "The 20% yield-reduction default is an editable planning scenario. The LIRF study reports wide "
        "variation by growth stage, severity, and year, so no single yield penalty is universally expected."
    )

    st.subheader("Source mapping")
    st.table(pd.DataFrame(SOURCE_MAPPING, columns=["Calculation or assumption", "Primary local source"]))
    for reference in REFERENCES:
        st.markdown(f"**{reference.title}** — {reference.authors}")
        st.write(f"Local source: `{reference.local_file}`. {reference.role}")
        st.markdown(f"[External source]({reference.url})")

    st.subheader("In-season uptake context")
    st.write(
        "UNL G2365 describes rapid cumulative plant N uptake from roughly V6 through R2 and encourages "
        "responsive in-season management. That context is educational only here. Cumulative plant N uptake "
        "is not equivalent to total N availability or fertilizer N requirement."
    )


_initialize_state()
st.sidebar.image(CSU_LOGO_URL, width=220)
st.sidebar.markdown("### Colorado Corn Nitrogen Planner")
st.sidebar.markdown(
    f"Created by [AJ Brown]({AUTHOR_WEBSITE}), Agricultural Data Scientist  \n"
    f"[Personal website]({AUTHOR_WEBSITE}) · [GitHub repository]({GITHUB_REPOSITORY})"
)
st.sidebar.divider()
page = st.sidebar.radio(
    "Navigation",
    ["Recommendations", "Compare Fields", "Methodology and References"],
    key="navigation",
)
st.sidebar.caption(
    "Decision-support and education only. Confirm recommendations with current soil and water tests and local agronomic advice."
)
if page == "Recommendations":
    recommendations_page()
elif page == "Compare Fields":
    compare_page()
else:
    methodology_page()
