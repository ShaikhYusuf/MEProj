# design/requirements_validator.py
from .requirements import RequirementsDocument

REQUIRED_NFR_CATEGORIES = {
    "performance", "security", "reliability",
}

def validate_requirements(doc: RequirementsDocument) -> list[str]:
    errors: list[str] = []

    actor_ids = {a.id for a in doc.actors}
    func_ids  = {r.id for r in doc.functional}
    nfr_ids   = {r.id for r in doc.non_functional}

    # 1. Unique IDs
    all_ids = [a.id for a in doc.actors] + list(func_ids) + list(nfr_ids)
    if len(all_ids) != len(set(all_ids)):
        errors.append("Duplicate IDs across actors / functional / non-functional.")

    # 2. Every functional req references a real actor
    for r in doc.functional:
        if r.actor_id not in actor_ids:
            errors.append(f"{r.id}: actor_id '{r.actor_id}' does not exist.")

    # 3. Every actor used by ≥1 functional req
    used = {r.actor_id for r in doc.functional}
    for a in doc.actors:
        if a.id not in used:
            errors.append(f"Actor {a.id} ({a.name}) has no functional requirement.")

    # 4. Every functional req has ≥1 acceptance criterion
    for r in doc.functional:
        if not r.acceptance_criteria:
            errors.append(f"{r.id}: missing acceptance criteria.")

    # 5. Every NFR has measurable metrics with units
    for n in doc.non_functional:
        if not n.metrics:
            errors.append(f"{n.id}: NFR has no measurable metric.")
        for m in n.metrics:
            if not m.unit.strip():
                errors.append(f"{n.id}: metric '{m.name}' has no unit.")

    # 6. Minimum NFR coverage
    covered = {n.category for n in doc.non_functional}
    missing = REQUIRED_NFR_CATEGORIES - covered
    if missing:
        errors.append(f"Missing mandatory NFR categories: {sorted(missing)}.")

    return errors