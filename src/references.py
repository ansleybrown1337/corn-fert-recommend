from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScientificReference:
    key: str
    title: str
    authors: str
    local_file: str
    role: str
    url: str


REFERENCES = (
    ScientificReference(
        key="csu",
        title="Fertilizing Irrigated Corn",
        authors="Davis, Brown, and Deiss; Colorado State University Extension",
        local_file="docs/Fertilizing Irrigated Corn - CSU Extension.url",
        role=(
            "Standard crop N need, residual soil nitrate, organic matter, irrigation-water "
            "credits, worked example, and timing context."
        ),
        url="https://extension.colostate.edu/resource/fertilizing-irrigated-corn/",
    ),
    ScientificReference(
        key="donovan",
        title="Excess nitrogen may decrease maize grain yields when water is limited",
        authors="Donovan et al. (2026), Agricultural Water Management 332:110456",
        local_file="docs/donovan_2026.pdf",
        role=(
            "Experimental 31% reduction in agronomic optimum total N availability under "
            "limited water; total availability included fertilizer, residual soil inorganic N, "
            "and irrigation-water N."
        ),
        url="https://doi.org/10.1016/j.agwat.2026.110456",
    ),
    ScientificReference(
        key="unl",
        title="In-Season Nitrogen Management for Irrigated Corn (G2365)",
        authors="Richard Ferguson, Nebraska Extension",
        local_file="docs/UNL N management.pdf",
        role=(
            "Educational context for uptake timing and in-season management; not used as a "
            "recommendation equation in this application."
        ),
        url="https://extensionpubs.unl.edu/publication/g2365/2024/html/view",
    ),
    ScientificReference(
        key="lirf",
        title="Response of Maize Yield Components to Growth Stage-Based Deficit Irrigation",
        authors="Drobnitch et al. (2019), Agronomy Journal 111:3244-3252",
        local_file="docs/LIRF deficit irrigation paper.pdf",
        role=(
            "Evidence that yield response varies with stress stage, severity, and year; supports "
            "treating the default 20% yield reduction only as an editable planning assumption."
        ),
        url="https://doi.org/10.2134/agronj2019.03.0214",
    ),
)


SOURCE_MAPPING = (
    ("CSU basal N equation", "docs/Fertilizing Irrigated Corn - CSU Extension.url"),
    ("Residual soil nitrate credit", "docs/Fertilizing Irrigated Corn - CSU Extension.url"),
    ("Organic matter credit", "docs/Fertilizing Irrigated Corn - CSU Extension.url"),
    ("Irrigation N conversion", "docs/Fertilizing Irrigated Corn - CSU Extension.url"),
    ("In-season uptake context", "docs/UNL N management.pdf"),
    ("31% water-limited N adjustment", "docs/donovan_2026.pdf"),
    ("Default yield-reduction planning assumption", "docs/LIRF deficit irrigation paper.pdf"),
)


METHODOLOGY_ROWS = (
    ("Crop N need", "35 + 1.2 x expected yield (bu/ac)", "CSU Extension"),
    ("Residual soil nitrate credit", "8 x 0-24 inch weighted mean NO3-N (ppm)", "CSU Extension"),
    ("Organic matter credit", "0.14 x expected yield (bu/ac) x organic matter (%)", "CSU Extension"),
    ("Irrigation-water N credit", "0.223 x water NO3-N (ppm) x irrigation applied through tasseling (ac-in)", "CSU Extension"),
    ("Soil nitrate unit conversion", "lb N/ac = ppm x 8 x sampled thickness / 24; factors are 2.667 (0-8 in), 5.333 (8-24 in), and 8.0 (0-24 in)", "Algebraic equivalent of CSU 0-24 inch weighted-mean method"),
    ("Standard fertilizer N", "max(0, crop N need - all N credits)", "CSU Extension framework"),
    ("Water-limited yield", "full-irrigation yield x (1 - editable yield reduction / 100)", "User-entered planning assumption"),
    ("Experimental N availability target", "yield-adjusted basal N need x (1 - Donovan reduction / 100)", "CSU framework combined with Donovan et al. (2026)"),
    ("Experimental fertilizer N", "max(0, experimental N target - all standard N credits); OM credit remains based on full-irrigation expected yield", "Explicit application-method choice for this tool"),
)
