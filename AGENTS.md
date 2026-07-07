# Repository guidance for coding agents

- Inspect the scientific references in `docs/` before changing agronomic logic.
- Keep scientific calculations separate from Streamlit UI code.
- Every agronomic equation and coefficient must remain traceable to a documented reference.
- Make every new scientific assumption visible to users and document it.
- Never silently change equation coefficients.
- Add or update unit tests for every calculation change.
- Preserve standard CSU mode independently of experimental drought mode.
- Preserve multi-field, scenario duplication, comparison, and batch calculation behavior.
- Keep stable field IDs independent of editable field names.
- Exports must include user inputs and intermediate calculations, not only final recommendations.
- Do not equate crop N need, N availability, fertilizer N, or plant N uptake.
- Do not add economic optimization unless the user explicitly requests it.

