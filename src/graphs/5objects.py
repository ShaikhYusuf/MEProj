# graphs/objects.py
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
from src.llm import get_instructor, MODEL_DESIGN
from src.design.requirements import RequirementsDocument
from src.design.er import ERModel
from src.design.usecases import UseCaseModel
from src.design.objects import ObjectModel
from src.design.objects_validator import validate_objects

class ObjectsState(BaseModel):
    requirements: RequirementsDocument
    er: ERModel
    usecases: UseCaseModel
    model: ObjectModel | None = None
    best_model: ObjectModel | None = None
    best_error_count: int = 10**9
    errors: list[str] = Field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 4

PROMPT = """Design the object model (the CONTRACT layer). Each object is a service/domain class with public methods.

Rules:
- Object ID OBJ-001. protocol_name ends with 'Protocol' (e.g. OrderServiceProtocol).
- Object.derived_from lists the UC-* IDs the object participates in.
- entity_refs lists ENT-* the object owns / manages.
- Each method: unique name within its object, params (name + type annotation + optional flag), return type.
- CRITICAL: each method's serves_steps lists the exact UC-<n>-S<nn> step IDs it implements.
- EVERY usecase step must be served by at least one method across all objects.
- Method's derived_from = the parent UC-* IDs.
- Use idiomatic Python types: UUID, str, int, float, datetime, list[X], dict[str, X], etc.

REQUIREMENTS:
{reqs}

ER:
{er}

USECASES:
{uc}
"""

REFINE = """Fix the object model. Return COMPLETE corrected model.

CURRENT:
{model}

ERRORS:
{errors}

REQUIREMENTS:
{reqs}

ER:
{er}

USECASES:
{uc}
"""

async def generate(s: ObjectsState) -> dict:
    c = get_instructor()
    m = await c.chat.completions.create(model=MODEL_DESIGN, response_model=ObjectModel, max_retries=3,
        messages=[{"role": "user", "content": PROMPT.format(
            reqs=s.requirements.model_dump_json(indent=2),
            er=s.er.model_dump_json(indent=2),
            uc=s.usecases.model_dump_json(indent=2))}])
    return {"model": m}

async def validate(s: ObjectsState) -> dict:
    errs = validate_objects(s.model, s.usecases, s.er)
    bm, bc = s.best_model, s.best_error_count
    if len(errs) < bc: bm, bc = s.model, len(errs)
    return {"errors": errs, "best_model": bm, "best_error_count": bc}

async def refine(s: ObjectsState) -> dict:
    c = get_instructor()
    m = await c.chat.completions.create(model=MODEL_DESIGN, response_model=ObjectModel, max_retries=3,
        messages=[{"role": "user", "content": REFINE.format(
            model=s.model.model_dump_json(indent=2),
            errors="\n".join(f"- {e}" for e in s.errors),
            reqs=s.requirements.model_dump_json(indent=2),
            er=s.er.model_dump_json(indent=2),
            uc=s.usecases.model_dump_json(indent=2))}])
    return {"model": m, "iteration": s.iteration + 1}

async def finalize(s: ObjectsState) -> dict:
    return {"model": s.best_model or s.model}

def _route(s: ObjectsState) -> str:
    if not s.errors or s.iteration >= s.max_iterations: return "finalize"
    return "refine"

class ObjectsGraph:
    def __init__(self) -> None:
        g = StateGraph(ObjectsState)
        g.add_node("generate", generate); g.add_node("validate", validate)
        g.add_node("refine", refine);     g.add_node("finalize", finalize)
        g.set_entry_point("generate"); g.add_edge("generate", "validate")
        g.add_conditional_edges("validate", _route, {"refine": "refine", "finalize": "finalize"})
        g.add_edge("refine", "validate"); g.add_edge("finalize", END)
        self.graph = g.compile()

    async def run(self, requirements: RequirementsDocument, er: ERModel, usecases: UseCaseModel) -> ObjectsState:
        return ObjectsState.model_validate(await self.graph.ainvoke(
            {"requirements": requirements, "er": er, "usecases": usecases}))

if __name__ == "__main__":
    import asyncio
    from pathlib import Path
    from src.design.requirements import RequirementsDocument
    from src.design.er import ERModel
    from src.design.usecases import UseCaseModel

    reqs = RequirementsDocument.model_validate_json(Path("src/input/requirements.json").read_text())
    er = ERModel.model_validate_json(Path("src/input/er.json").read_text())
    uc = UseCaseModel.model_validate_json(Path("src/input/usecases.json").read_text())
    state = asyncio.run(ObjectsGraph().run(reqs, er, uc))

    print(f"Iterations: {state.iteration}, Errors: {len(state.errors)}")
    for e in state.errors:
        print("  -", e)
    if state.model:
        Path("src/input/objects.json").write_text(state.model.model_dump_json(indent=2))
        print(f"Saved: src/input/objects.json ({len(state.model.objects)} objects)")            