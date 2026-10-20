# graphs/er.py
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from src.llm import get_instructor, MODEL_DESIGN
from src.design.requirements import RequirementsDocument
from src.design.er import ERModel
from src.design.er_validator import validate_er

class ERState(BaseModel):
    requirements: RequirementsDocument
    model: ERModel | None = None
    best_model: ERModel | None = None
    best_error_count: int = 10**9
    errors: list[str] = Field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 3

ER_PROMPT = """Produce an ER model from the requirements document below.

Rules:
- Each entity has unique name, exactly one primary-key attribute, and 1+ non-PK attributes.
- Each entity's derived_from MUST reference the REQ-* / NFR-* IDs that justify it.
- Relations use cardinality 1:1 | 1:N | N:1 | N:M and reference existing entity names.
- No orphan entities (each must trace to ≥1 requirement).

REQUIREMENTS:
{reqs_json}
"""

ER_REFINE_PROMPT = """Fix the ER model based on validation errors. Return the COMPLETE corrected model.

CURRENT MODEL:
{model_json}

VALIDATION ERRORS:
{errors}

REQUIREMENTS (for reference):
{reqs_json}
"""

async def er_generate(state: ERState) -> dict:
    client = get_instructor()
    model = await client.chat.completions.create(
        model=MODEL_DESIGN,
        response_model=ERModel,
        messages=[{"role": "user", "content": ER_PROMPT.format(
            reqs_json=state.requirements.model_dump_json(indent=2))}],
        max_retries=3,
    )
    return {"model": model}

async def er_validate(state: ERState) -> dict:
    errors = validate_er(state.model, state.requirements)
    best_model, best_count = state.best_model, state.best_error_count
    if len(errors) < best_count:
        best_model, best_count = state.model, len(errors)
    return {"errors": errors, "best_model": best_model, "best_error_count": best_count}

async def er_refine(state: ERState) -> dict:
    client = get_instructor()
    model = await client.chat.completions.create(
        model=MODEL_DESIGN,
        response_model=ERModel,
        messages=[{"role": "user", "content": ER_REFINE_PROMPT.format(
            model_json=state.model.model_dump_json(indent=2),
            errors="\n".join(f"- {e}" for e in state.errors),
            reqs_json=state.requirements.model_dump_json(indent=2))}],
        max_retries=3,
    )
    return {"model": model, "iteration": state.iteration + 1}

async def er_finalize(state: ERState) -> dict:
    return {"model": state.best_model or state.model}

def _route(state: ERState) -> str:
    if not state.errors or state.iteration >= state.max_iterations:
        return "finalize"
    return "refine"

class ERGraph:
    def __init__(self) -> None:
        g = StateGraph(ERState)
        g.add_node("generate", er_generate)
        g.add_node("validate", er_validate)
        g.add_node("refine",   er_refine)
        g.add_node("finalize", er_finalize)
        g.set_entry_point("generate")
        g.add_edge("generate", "validate")
        g.add_conditional_edges("validate", _route, {"refine": "refine", "finalize": "finalize"})
        g.add_edge("refine", "validate")
        g.add_edge("finalize", END)
        self.graph = g.compile()

    async def run(self, requirements: RequirementsDocument) -> ERState:
        return ERState.model_validate(await self.graph.ainvoke({"requirements": requirements}))


if __name__ == "__main__":
    import asyncio
    from pathlib import Path
    from src.design.requirements import RequirementsDocument

    reqs = RequirementsDocument.model_validate_json(
        Path("src/input/requirements.json").read_text()
    )
    state = asyncio.run(ERGraph().run(reqs))

    print(f"Iterations: {state.iteration}")
    print(f"Errors: {len(state.errors)}")
    for e in state.errors:
        print("  -", e)

    if state.model:
        Path("src/input/er.json").write_text(state.model.model_dump_json(indent=2))
        print(f"\nSaved: src/input/er.json ({len(state.model.entities)} entities)")