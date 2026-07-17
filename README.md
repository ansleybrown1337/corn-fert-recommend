# Colorado Corn Nitrogen Planner

A multi-field Streamlit decision-support application for irrigated grain-corn nitrogen planning in Colorado. The standard calculation implements the Colorado State University Extension publication **Fertilizing Irrigated Corn**. An optional experimental mode combines the CSU yield-based framework with water x nitrogen research from Donovan et al. (2026).

A field entry may represent a physical field, a plot, or a hypothetical management scenario. Users can add, duplicate, rename, remove, and reorder fields, compare results, and download reproducible CSV, Excel, or printable PDF outputs.

## Scientific scope

The standard CSU calculation is:

```text
crop N need = 35 + 1.2 x expected yield (bu/ac)
residual soil nitrate credit = 8 x weighted mean 0-24 inch NO3-N (ppm)
organic matter credit = 0.14 x expected yield (bu/ac) x organic matter (%)
irrigation-water N credit = 0.223 x water NO3-N (ppm) x irrigation through tasseling (acre-inches)
fertilizer N = max(0, crop N need - all N credits)
```

The app retains the unbounded balance when credits exceed a target, while displaying a fertilizer recommendation of zero. Soil nitrate may be entered directly as a depth-weighted 0-24 inch value or as ordered soil layers, in either ppm NO3-N or lb nitrate-N/ac. The lb/ac conversion is the algebraic equivalent of CSU's 8 lb N/ac per ppm over 24 inches: factors are 2.667 for 0-8 inches, 5.333 for 8-24 inches, and 8.0 for 0-24 inches. Layer inputs must be contiguous and cover 0-24 inches; the app does not extrapolate through gaps or unsampled depth.

The experimental drought calculation is:

```text
water-limited yield = full-irrigation yield x (1 - yield reduction / 100)
full-yield basal N need = 35 + 1.2 x full-irrigation yield
experimental N availability target = full-yield basal N need x (1 - Donovan reduction / 100)
experimental fertilizer N = max(0, experimental target - standard CSU N credits)
```

The water-limited yield value is displayed as scenario context and is not used as an additional multiplier on the Donovan adjustment. The 31% default is applied to the target N availability framework, not to fertilizer alone. Donovan et al. defined total N availability using fertilizer N, residual soil inorganic N, and irrigation-water N. The adjustment is applied before standard CSU credits are subtracted, and the standard CSU recommendation remains visible beside the experimental result.

**The experimental drought adjustment is a research-informed extrapolation and has not been validated as a CSU fertilizer recommendation algorithm.**

## Source mapping

The local `docs/` library was inspected before implementation.

| Calculation or assumption | Primary local source |
| --- | --- |
| CSU basal N equation | `docs/Fertilizing Irrigated Corn - CSU Extension.url` |
| Residual soil nitrate credit | `docs/Fertilizing Irrigated Corn - CSU Extension.url` |
| Organic matter credit | `docs/Fertilizing Irrigated Corn - CSU Extension.url` |
| Irrigation N conversion | `docs/Fertilizing Irrigated Corn - CSU Extension.url` |
| In-season uptake context | `docs/UNL N management.pdf` |
| 31% water-limited N adjustment | `docs/donovan_2026.pdf` |
| Default water-limited yield-reduction assumption | `docs/LIRF deficit irrigation paper.pdf` |

The CSU `.url` shortcut points to the peer-reviewed CSU Extension page [Fertilizing Irrigated Corn](https://extension.colostate.edu/resource/fertilizing-irrigated-corn/), reviewed in September 2025. That page supports the four standard coefficients and the 225 bu/ac worked example.

Donovan et al., *Excess nitrogen may decrease maize grain yields when water is limited*, Agricultural Water Management 332 (2026) 110456, reports an average 31% lower agronomic optimum total N availability under limited water. [DOI](https://doi.org/10.1016/j.agwat.2026.110456)

The USDA-ARS Limited Irrigation Research Farm paper, *Response of Maize Yield Components to Growth Stage-Based Deficit Irrigation* (2019), reports substantially different yield reductions by stress stage, severity, and year. Its results do not support a universal 20% yield penalty. The app therefore retains 20% only as a visible, user-editable planning assumption for scenario analysis. [DOI](https://doi.org/10.2134/agronj2019.03.0214)

UNL G2365 is used only for educational context on rapid crop N uptake from approximately V6 through R2 and the value of in-season management. Its uptake curve is not used as a fertilizer recommendation equation. Cumulative plant N uptake is not equivalent to total N availability or fertilizer N requirement.

The reference workbook `docs/2026 Fertilizer application calcs TAPS.xlsx` was also inspected. It reflects the earlier supplied scenario arithmetic (210 bu/ac, 20% yield reduction, 168 bu/ac, 236.6 lb N/ac basal target, and 163.254 lb N/ac after a 31% reduction) but is not treated as the scientific authority for coefficients. The current app avoids applying that yield-reduction assumption as a second N-target reduction.

## Functionality

- Independent inputs and calculations for multiple fields or scenarios
- Stable internal field IDs independent of editable display names
- Add, duplicate, remove, rename, and reorder field scenarios
- Direct or layer-based 0-24 inch soil nitrate input with validation
- Soil nitrate entry in ppm NO3-N or lb nitrate-N/ac, with depth-specific conversion
- Standard CSU result and optional experimental drought result shown together
- Field-level stacked N balance chart with target reference lines
- Multi-field recommendation and N-source comparison charts
- CSV export with inputs, intermediate calculations, unbounded balances, and outputs
- Formatted Excel export with `Summary`, `Inputs`, `N Balance`, and `Methodology` sheets
- Printable multi-field PDF report with bar charts, inputs, intermediate calculations, recommendations, methodology, and references
- Pure, typed calculation functions with unit tests

## Install and run

Python 3.11 or newer is recommended.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Run tests:

```powershell
python -m pytest
```

## Project structure

```text
app.py                 Streamlit interface
src/models.py          Typed field and result structures
src/calculations.py    Pure agronomic calculations
src/validation.py      Scientific input validation
src/charts.py          Plotly visualizations
src/exports.py         CSV, Excel, and PDF exports
src/references.py      Source metadata and methodology mapping
src/text.py            Field-specific interpretations
src/state.py           Stable field/scenario state helpers
tests/                 Calculation, validation, batch, and export tests
docs/                  Local scientific reference library
```

## Scientific limitations

- This is an educational decision-support tool, not a guarantee of N sufficiency or crop response.
- The CSU framework assumes realistic expected yield, adequate irrigation, and appropriate management.
- The drought mode is an explicit extrapolation combining separate CSU and Donovan frameworks; it has not been field-validated as an integrated recommendation algorithm.
- The 20% default yield reduction is a planning scenario, not a forecast, and is reported as yield context rather than used to scale the Donovan N target. Stress timing, severity, weather, soil water, and hybrid response can materially change yield loss.
- The same standard CSU credits, including the organic matter credit calculated from the full-irrigation expected yield, are subtracted from both targets. This is a transparent version-1 methodological choice requiring agronomic review before operational adoption.
- Soil tests, irrigation-water tests, and locally appropriate crop/manure credits remain the user's responsibility.
- Irrigation-water N credit uses only irrigation expected from planting through tasseling, consistent with the CSU recommendation framework used here.
- No fertilizer price, grain price, or economic optimization is included.
