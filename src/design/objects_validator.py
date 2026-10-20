# design/objects_validator.py
from .objects import ObjectModel
from .usecases import UseCaseModel
from .er import ERModel

def validate_objects(om: ObjectModel, uc: UseCaseModel, er: ERModel) -> list[str]:
    errors: list[str] = []
    entity_names = {e.name for e in er.entities}
    step_ids = {s.id for u in uc.usecases for s in u.steps}
    uc_ids = {u.id for u in uc.usecases}

    obj_names: set[str] = set()
    method_names_by_obj: dict[str, set[str]] = {}

    for o in om.objects:
        if o.name in obj_names:
            errors.append(f"Duplicate object name: {o.name}.")
        obj_names.add(o.name)
        if not o.protocol_name.endswith("Protocol"):
            errors.append(f"Object {o.name}: protocol_name '{o.protocol_name}' must end with 'Protocol'.")
        for e in o.entity_refs:
            if e not in entity_names:
                errors.append(f"Object {o.name}: entity_ref '{e}' unknown.")
        for mid in o.derived_from:
            if mid not in uc_ids:
                errors.append(f"Object {o.name}: derived_from '{mid}' not a usecase.")

        seen = set()
        for m in o.methods:
            if m.name in seen:
                errors.append(f"Object {o.name}: duplicate method '{m.name}'.")
            seen.add(m.name)
            for sid in m.serves_steps:
                if sid not in step_ids:
                    errors.append(f"Method {o.name}.{m.name}: serves_steps '{sid}' unknown.")
            for mid in m.derived_from:
                if mid not in uc_ids:
                    errors.append(f"Method {o.name}.{m.name}: derived_from '{mid}' not a usecase.")
        method_names_by_obj[o.name] = seen

    # Coverage: every step is served by ≥1 method
    served = {sid for o in om.objects for m in o.methods for sid in m.serves_steps}
    uncovered = step_ids - served
    if uncovered:
        errors.append(f"Usecase steps not served by any method: {sorted(uncovered)}.")

    return errors