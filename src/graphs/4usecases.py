# graphs/usecases.py
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
from src.llm import get_instructor, MODEL_DESIGN
from src.design.requirements import RequirementsDocument
from src.design.er import ERModel
from src.design.usecases import UseCaseModel
from src.design.usecases_validator import validate_usecases

class UseCasesState(BaseModel):
    requirements: RequirementsDocument
    er: ERModel
    model: UseCaseModel | None = None
    best_model: UseCaseModel | None = None
    best_error_count: int = 10**9
    errors: list[str] = Field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 4

PROMPT = """Produce the use-case model. One use case per coherent workflow.

Rules:
- ID format UC-001. primary_actor_id must be an existing ACT-* ID.
- Every use case's derived_from MUST include the REQ-* IDs it fulfills.
- Every functional requirement MUST be covered by ≥1 use case.
- Steps are numbered 1..N sequentially, ID format <UC-ID>-S<NN>.
- Each step: description, optional actor_id (None = system internal), entity_refs = list of ENT-* touched.
- Pre/postconditions are free-text sentences.

REQUIREMENTS:
{reqs}

ER MODEL:
{er}
"""

REFINE = """Fix the use-case model. Return COMPLETE corrected model.

CURRENT:
{model}

ERRORS:
{errors}

REQUIREMENTS:
{reqs}

ER:
{er}
"""

async def generate(s: UseCasesState) -> dict:
    c = get_instructor()
    m = await c.chat.completions.create(model=MODEL_DESIGN, response_model=UseCaseModel, max_retries=3,
        messages=[{"role": "user", "content": PROMPT.format(
            reqs=s.requirements.model_dump_json(indent=2),
            er=s.er.model_dump_json(indent=2))}])
    return {"model": m}

async def validate(s: UseCasesState) -> dict:
    errs = validate_usecases(s.model, s.requirements, s.er)
    bm, bc = s.best_model, s.best_error_count
    if len(errs) < bc: bm, bc = s.model, len(errs)
    return {"errors": errs, "best_model": bm, "best_error_count": bc}

async def refine(s: UseCasesState) -> dict:
    c = get_instructor()
    m = await c.chat.completions.create(model=MODEL_DESIGN, response_model=UseCaseModel, max_retries=3,
        messages=[{"role": "user", "content": REFINE.format(
            model=s.model.model_dump_json(indent=2),
            errors="\n".join(f"- {e}" for e in s.errors),
            reqs=s.requirements.model_dump_json(indent=2),
            er=s.er.model_dump_json(indent=2))}])
    return {"model": m, "iteration": s.iteration + 1}

async def finalize(s: UseCasesState) -> dict:
    return {"model": s.best_model or s.model}

def _route(s: UseCasesState) -> str:
    if not s.errors or s.iteration >= s.max_iterations: return "finalize"
    return "refine"

class UseCasesGraph:
    def __init__(self) -> None:
        g = StateGraph(UseCasesState)
        g.add_node("generate", generate); g.add_node("validate", validate)
        g.add_node("refine", refine);     g.add_node("finalize", finalize)
        g.set_entry_point("generate"); g.add_edge("generate", "validate")
        g.add_conditional_edges("validate", _route, {"refine": "refine", "finalize": "finalize"})
        g.add_edge("refine", "validate"); g.add_edge("finalize", END)
        self.graph = g.compile()

    async def run(self, requirements: RequirementsDocument, er: ERModel) -> UseCasesState:
        return UseCasesState.model_validate(await self.graph.ainvoke({"requirements": requirements, "er": er}))

if __name__ == "__main__":
    import asyncio
    from pathlib import Path
    from src.design.requirements import RequirementsDocument
    from src.design.er import ERModel

    reqs = RequirementsDocument.model_validate_json(Path("src/input/requirements.json").read_text())
    er = ERModel.model_validate_json(Path("src/input/er.json").read_text())
    state = asyncio.run(UseCasesGraph().run(reqs, er))

    print(f"Iterations: {state.iteration}, Errors: {len(state.errors)}")
    for e in state.errors:
        print("  -", e)
    if state.model:
        Path("input/src/usecases.json").write_text(state.model.model_dump_json(indent=2))
        print(f"Saved: src/input/usecases.json ({len(state.model.usecases)} usecases)")    