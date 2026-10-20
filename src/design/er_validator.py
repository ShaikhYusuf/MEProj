# design/er_validator.py
from .er import ERModel
from .requirements import RequirementsDocument

def validate_er(er: ERModel, reqs: RequirementsDocument) -> list[str]:
    errors: list[str] = []
    entity_names = [e.name for e in er.entities]

    if len(entity_names) != len(set(entity_names)):
        errors.append("Duplicate entity names.")

    req_ids = {r.id for r in reqs.functional} | {r.id for r in reqs.non_functional}

    for e in er.entities:
        if not e.derived_from:
            errors.append(f"Entity {e.name}: derived_from empty.")
        for rid in e.derived_from:
            if rid not in req_ids:
                errors.append(f"Entity {e.name}: derived_from '{rid}' not in requirements.")
        pk = [a for a in e.attributes if a.primary_key]
        if len(pk) != 1:
            errors.append(f"Entity {e.name}: must have exactly 1 primary key (has {len(pk)}).")

    for r in er.relations:
        if r.from_entity not in entity_names:
            errors.append(f"Relation: from_entity '{r.from_entity}' unknown.")
        if r.to_entity not in entity_names:
            errors.append(f"Relation: to_entity '{r.to_entity}' unknown.")

    return errors