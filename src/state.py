from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from .models import FieldScenario


def new_field(index: int) -> FieldScenario:
    return FieldScenario(field_name=f"Field {index}")


def duplicate_field(field: FieldScenario, existing_count: int) -> FieldScenario:
    duplicate = deepcopy(field)
    duplicate.field_id = str(uuid4())
    duplicate.field_name = f"{field.field_name} copy"
    if not duplicate.scenario_description:
        duplicate.scenario_description = f"Scenario duplicated from {field.field_name}"
    return duplicate


def move_field(fields: list[FieldScenario], index: int, offset: int) -> None:
    target = index + offset
    if 0 <= index < len(fields) and 0 <= target < len(fields):
        fields[index], fields[target] = fields[target], fields[index]

