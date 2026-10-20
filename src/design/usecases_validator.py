# design/usecases_validator.py
from .usecases import UseCaseModel
from .requirements import RequirementsDocument
from .er import ERModel

def validate_usecases(uc: UseCaseModel, reqs: RequirementsDocument, er: ERModel) -> list[str]:
    errors: list[str] = []
    actor_ids = {a.id for a in reqs.actors}
    entity_names = {e.name for e in er.entities}
    req_ids = {r.id for r in reqs.functional} | {r.id for r in reqs.non_functional}

    covered_reqs: set[str] = set()
    all_step_ids: set[str] = set()
    all_uc_ids: set[str] = set()

    for u in uc.usecases:
        if u.id in all_uc_ids:
            errors.append(f"Duplicate usecase ID: {u.id}.")
        all_uc_ids.add(u.id)

        if u.primary_actor_id not in actor_ids:
            errors.append(f"{u.id}: primary_actor_id '{u.primary_actor_id}' unknown.")
        for sa in u.supporting_actor_ids:
            if sa not in actor_ids:
                errors.append(f"{u.id}: supporting actor '{sa}' unknown.")

        if not u.derived_from:
            errors.append(f"{u.id}: derived_from empty.")
        for rid in u.derived_from:
            if rid not in req_ids:
                errors.append(f"{u.id}: derived_from '{rid}' unknown.")
            else:
                covered_reqs.add(rid)

        orders = [s.order for s in u.steps]
        if orders != sorted(orders) or orders != list(range(1, len(orders) + 1)):
            errors.append(f"{u.id}: step orders must be 1..N sequential.")
        if len({s.id for s in u.steps}) != len(u.steps):
            errors.append(f"{u.id}: duplicate step IDs.")

        for s in u.steps:
            if s.id in all_step_ids:
                errors.append(f"Duplicate step ID: {s.id}.")
            all_step_ids.add(s.id)
            if s.actor_id is not None and s.actor_id not in actor_ids:
                errors.append(f"{s.id}: actor '{s.actor_id}' unknown.")
            for er_ref in s.entity_refs:
                if er_ref not in entity_names:
                    errors.append(f"{s.id}: entity_ref '{er_ref}' unknown.")

    # Coverage: every functional req has ≥1 UC
    func_ids = {r.id for r in reqs.functional}
    missing = func_ids - covered_reqs
    if missing:
        errors.append(f"Functional requirements not covered by any usecase: {sorted(missing)}.")

    return errors