# graphs/sequence.py
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
from src.llm import get_instructor, MODEL_DESIGN
from src.design.requirements import RequirementsDocument
from src.design.objects import ObjectModel
from src.design.usecases import UseCaseModel
from src.design.sequence import SequenceModel
from src.design.sequence_validator import validate_sequences

class SequenceState(BaseModel):
    requirements: RequirementsDocument
    objects: ObjectModel
    usecases: UseCaseModel
    model: SequenceModel | None = None
    best_model: SequenceModel | None = None
    best_error_count: int = 10**9
    errors: list[str] = Field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 4

PROMPT = """Produce one sequence per usecase (top-level: actor ↔ system object).

Rules:
- ID format SEQ-001. derived_from = the UC-* ID this sequence realizes.
- Every usecase must have exactly one sequence covering it.
- Messages ordered by ascending 'order' field.
- from_id ∈ {ACT-* actor IDs, OBJ-* object names}.
- to_id MUST be an object name from the object model.
- method MUST be a declared method on that object (exact name match).
- args must have the same count as the method's params.
- Only top-level orchestration — one call per step; do NOT expand internals.

REQUIREMENTS actors:
{actors}

OBJECTS (with method signatures):
{objects}

USECASES:
{usecases}
"""

REFINE = """Fix the sequence model. Return COMPLETE corrected model.

CURRENT:
{model}

ERRORS:
{errors}

OBJECTS:
{objects}

USECASES:
{usecases}
"""

def _objects_with_sigs(om: ObjectModel) -> str:
    lines = []
    for o in om.objects:
        lines.append(f"Object {o.name}:")
        for m in o.methods:
            ps = ", ".join(f"{p.name}:{p.type}" for p in m.params)
            lines.append(f"  - {m.name}({ps}) -> {m.returns}   [serves {m.serves_steps}]")
    return "\n".join(lines)

async def generate(s: SequenceState) -> dict:
    c = get_instructor()
    m = await c.chat.completions.create(model=MODEL_DESIGN, response_model=SequenceModel, max_retries=3,
        messages=[{"role": "user", "content": PROMPT.format(
            actors="\n".join(f"{a.id} {a.name}" for a in s.requirements.actors),
            objects=_objects_with_sigs(s.objects),
            usecases=s.usecases.model_dump_json(indent=2))}])
    return {"model": m}

async def validate(s: SequenceState) -> dict:
    errs = validate_sequences(s.model, s.objects, s.requirements, s.usecases)
    bm, bc = s.best_model, s.best_error_count
    if len(errs) < bc: bm, bc = s.model, len(errs)
    return {"errors": errs, "best_model": bm, "best_error_count": bc}

async def refine(s: SequenceState) -> dict:
    c = get_instructor()
    m = await c.chat.completions.create(model=MODEL_DESIGN, response_model=SequenceModel, max_retries=3,
        messages=[{"role": "user", "content": REFINE.format(
            model=s.model.model_dump_json(indent=2),
            errors="\n".join(f"- {e}" for e in s.errors),
            objects=_objects_with_sigs(s.objects),
            usecases=s.usecases.model_dump_json(indent=2))}])
    return {"model": m, "iteration": s.iteration + 1}

async def finalize(s: SequenceState) -> dict:
    return {"model": s.best_model or s.model}

def _route(s: SequenceState) -> str:
    if not s.errors or s.iteration >= s.max_iterations: return "finalize"
    return "refine"

class SequenceGraph:
    def __init__(self) -> None:
        g = StateGraph(SequenceState)
        g.add_node("generate", generate); g.add_node("validate", validate)
        g.add_node("refine", refine);     g.add_node("finalize", finalize)
        g.set_entry_point("generate"); g.add_edge("generate", "validate")
        g.add_conditional_edges("validate", _route, {"refine": "refine", "finalize": "finalize"})
        g.add_edge("refine", "validate"); g.add_edge("finalize", END)
        self.graph = g.compile()

    async def run(self, requirements: RequirementsDocument, objects: ObjectModel, usecases: UseCaseModel) -> SequenceState:
        return SequenceState.model_validate(await self.graph.ainvoke(
            {"requirements": requirements, "objects": objects, "usecases": usecases}))

if __name__ == "__main__":
    import asyncio
    from pathlib import Path
    from src.design.requirements import RequirementsDocument
    from src.design.objects import ObjectModel
    from src.design.usecases import UseCaseModel

    reqs = RequirementsDocument.model_validate_json(Path("src/input/requirements.json").read_text())
    obj = ObjectModel.model_validate_json(Path("src/input/objects.json").read_text())
    uc = UseCaseModel.model_validate_json(Path("src/input/usecases.json").read_text())
    state = asyncio.run(SequenceGraph().run(reqs, obj, uc))

    print(f"Iterations: {state.iteration}, Errors: {len(state.errors)}")
    for e in state.errors:
        print("  -", e)
    if state.model:
        Path("src/input/sequence.json").write_text(state.model.model_dump_json(indent=2))
        print(f"Saved: src/input/sequence.json ({len(state.model.sequences)} sequences)")