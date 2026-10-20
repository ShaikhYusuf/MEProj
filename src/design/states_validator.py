# design/states_validator.py
from .states import StateModel
from .er import ERModel
from .requirements import RequirementsDocument

def validate_states(sm: StateModel, er: ERModel, reqs: RequirementsDocument) -> list[str]:
    errors: list[str] = []
    entity_names = {e.name for e in er.entities}
    req_ids = {r.id for r in reqs.functional} | {r.id for r in reqs.non_functional}

    for m in sm.machines:
        if m.entity_id not in entity_names:
            errors.append(f"StateMachine {m.id}: entity_id '{m.entity_id}' not in ER.")
        for rid in m.derived_from:
            if rid not in req_ids:
                errors.append(f"StateMachine {m.id}: derived_from '{rid}' unknown.")

        names = [s.name for s in m.states]
        if len(names) != len(set(names)):
            errors.append(f"StateMachine {m.id}: duplicate state names.")
        for s in m.states:
            if s.entity_id != m.entity_id:
                errors.append(f"StateMachine {m.id}: state '{s.name}' owns entity '{s.entity_id}', expected '{m.entity_id}'.")

        initials = [s for s in m.states if s.is_initial]
        if len(initials) != 1:
            errors.append(f"StateMachine {m.id}: must have exactly 1 initial state (has {len(initials)}).")

        for t in m.transitions:
            if t.from_state not in names:
                errors.append(f"Transition {t.id}: from_state '{t.from_state}' unknown.")
            if t.to_state not in names:
                errors.append(f"Transition {t.id}: to_state '{t.to_state}' unknown.")

        # Reachability from initial
        if len(initials) == 1:
            reachable = {initials[0].name}
            changed = True
            while changed:
                changed = False
                for t in m.transitions:
                    if t.from_state in reachable and t.to_state not in reachable:
                        reachable.add(t.to_state); changed = True
            unreachable = set(names) - reachable
            if unreachable:
                errors.append(f"StateMachine {m.id}: unreachable states {sorted(unreachable)}.")

    return errors