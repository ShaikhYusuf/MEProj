# design/sequence_validator.py
from .sequence import SequenceModel
from .objects import ObjectModel
from .requirements import RequirementsDocument
from .usecases import UseCaseModel

def validate_sequences(
    seq: SequenceModel, om: ObjectModel, reqs: RequirementsDocument, uc: UseCaseModel
) -> list[str]:
    errors: list[str] = []

    actor_ids = {a.id for a in reqs.actors}
    objects = {o.name: o for o in om.objects}
    method_sigs = {
        o.name: {m.name: m for m in o.methods} for o in om.objects
    }
    uc_ids = {u.id for u in uc.usecases}

    covered_ucs: set[str] = set()

    for s in seq.sequences:
        if not s.derived_from:
            errors.append(f"{s.id}: derived_from empty (must reference a UC-*).")
        for uid in s.derived_from:
            if uid not in uc_ids:
                errors.append(f"{s.id}: derived_from '{uid}' unknown.")
            else:
                covered_ucs.add(uid)

        orders = [m.order for m in s.messages]
        if orders != sorted(orders):
            errors.append(f"{s.id}: messages must be ordered by ascending order.")

        for m in s.messages:
            # from_id must be actor or object
            if m.from_id not in actor_ids and m.from_id not in objects:
                errors.append(f"{s.id}: from_id '{m.from_id}' is neither actor nor object.")
            # to_id must be object
            if m.to_id not in objects:
                errors.append(f"{s.id}: to_id '{m.to_id}' is not an object.")
                continue
            # method must exist
            sig = method_sigs[m.to_id].get(m.method)
            if sig is None:
                errors.append(
                    f"{s.id}: message '{m.method}' not declared on {m.to_id} "
                    f"(available: {sorted(method_sigs[m.to_id])})."
                )
                continue
            # arity match (ignore self)
            if len(m.args) != len(sig.params):
                errors.append(
                    f"{s.id}: {m.to_id}.{m.method} expects {len(sig.params)} args, "
                    f"message passes {len(m.args)}."
                )

    # Every usecase has ≥1 sequence
    missing = uc_ids - covered_ucs
    if missing:
        errors.append(f"Usecases without any sequence: {sorted(missing)}.")

    return errors