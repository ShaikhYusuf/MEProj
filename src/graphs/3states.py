# graphs/states.py
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from src.llm import get_instructor, MODEL_DESIGN
from src.design.requirements import RequirementsDocument
from src.design.er import ERModel
from src.design.states import StateModel
from src.design.states_validator import validate_states

class StatesState(BaseModel):
    requirements: RequirementsDocument
    er: ERModel
    model: StateModel | None = None
    best_model: StateModel | None = None
    best_error_count: int = 10**9
    errors: list[str] = Field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 3

STATES_PROMPT = """Model the lifecycle states of every entity that has a meaningful state machine (Order, Payment, Account, Ticket, etc.).

For each machine:
- entity_id must be an existing ENT-* name from the ER model.
- Every state's entity_id equals the machine's entity_id.
- Exactly 1 is_initial=true state; any number of is_terminal=true states.
- Every transition: unique id (TRN-001), from_state, to_state, trigger (a domain event or method name), optional guard.
- Every state must be reachable from the initial state.
- All states and transitions must trace to requirements (derived_from).

Skip entities without a lifecycle (e.g. lookup tables, join tables).

REQUIREMENTS:
{reqs}

ER MODEL:
{er}
"""

STATES_REFINE = """Fix the state machines based on validation errors. Return COMPLETE corrected model.

CURRENT:
{model}

ERRORS:
{errors}

REQUIREMENTS:
{reqs}

ER:
{er}
"""

async def generate(s: StatesState) -> dict:
    c = get_instructor()
    m = await c.chat.completions.create(
        model=MODEL_DESIGN, response_model=StateModel, max_retries=3,
        messages=[{"role": "user", "content": STATES_PROMPT.format(
            reqs=s.requirements.model_dump_json(indent=2),
            er=s.er.model_dump_json(indent=2))}],
    )
    return {"model": m}

async def validate(s: StatesState) -> dict:
    errs = validate_states(s.model, s.er, s.requirements)
    best_m, best_c = s.best_model, s.best_error_count
    if len(errs) < best_c:
        best_m, best_c = s.model, len(errs)
    return {"errors": errs, "best_model": best_m, "best_error_count": best_c}

async def refine(s: StatesState) -> dict:
    c = get_instructor()
    m = await c.chat.completions.create(
        model=MODEL_DESIGN, response_model=StateModel, max_retries=3,
        messages=[{"role": "user", "content": STATES_REFINE.format(
            model=s.model.model_dump_json(indent=2),
            errors="\n".join(f"- {e}" for e in s.errors),
            reqs=s.requirements.model_dump_json(indent=2),
            er=s.er.model_dump_json(indent=2))}],
    )
    return {"model": m, "iteration": s.iteration + 1}

async def finalize(s: StatesState) -> dict:
    return {"model": s.best_model or s.model}

def _route(s: StatesState) -> str:
    if not s.errors or s.iteration >= s.max_iterations:
        return "finalize"
    return "refine"

class StatesGraph:
    def __init__(self) -> None:
        g = StateGraph(StatesState)
        g.add_node("generate", generate); g.add_node("validate", validate)
        g.add_node("refine", refine);     g.add_node("finalize", finalize)
        g.set_entry_point("generate")
        g.add_edge("generate", "validate")
        g.add_conditional_edges("validate", _route, {"refine": "refine", "finalize": "finalize"})
        g.add_edge("refine", "validate")
        g.add_edge("finalize", END)
        self.graph = g.compile()

    async def run(self, requirements: RequirementsDocument, er: ERModel) -> StatesState:
        return StatesState.model_validate(await self.graph.ainvoke({"requirements": requirements, "er": er}))

if __name__ == "__main__":
    import asyncio
    from pathlib import Path
    from src.design.requirements import RequirementsDocument
    from src.design.er import ERModel

    reqs = RequirementsDocument.model_validate_json(Path("src/input/requirements.json").read_text())
    er = ERModel.model_validate_json(Path("src/input/er.json").read_text())
    state = asyncio.run(StatesGraph().run(reqs, er))

    print(f"Iterations: {state.iteration}, Errors: {len(state.errors)}")
    for e in state.errors:
        print("  -", e)
    if state.model:
        Path("src/input/states.json").write_text(state.model.model_dump_json(indent=2))
        print(f"Saved: src/input/states.json ({len(state.model.machines)} machines)")