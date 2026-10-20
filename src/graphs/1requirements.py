# graphs/requirements.py
from __future__ import annotations
import json
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from src.llm import get_instructor, MODEL_DESIGN
from src.design.requirements import RequirementsDocument
from src.design.requirements_validator import validate_requirements

# ---------- State ----------
class RequirementsState(BaseModel):
    raw_input: str
    doc: RequirementsDocument | None = None
    best_doc: RequirementsDocument | None = None
    best_error_count: int = 10**9
    errors: list[str] = Field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 4
    done: bool = False

# ---------- Prompts ----------
EXTRACT_PROMPT = """You are a senior business analyst. Extract the COMPLETE requirements document from the input below.

Rules:
- Identify ALL actors: human users, external systems, scheduled jobs, admins. Each must have a unique ID (ACT-001) and kind (human | system | external | scheduled).
- Extract ALL functional requirements. Each must have: unique ID (REQ-001), title, description, actor_id, priority, and 1+ Given/When/Then acceptance criteria.
- Extract ALL non-functional requirements across every category present in the input: performance, scalability, security, usability, reliability, maintainability, portability, compliance. Each must have unique ID (NFR-001) and at least one measurable metric (name, numeric value, unit, comparison operator).
- Every actor must be referenced by at least one functional requirement.
- Record assumptions and open questions separately.
- Do not invent requirements not implied by the input.

INPUT:
<<<
{raw_input}
>>>
"""

AUDIT_PROMPT = """You previously extracted the requirements document below. Review it against the original input for COMPLETENESS and return a corrected document.

ORIGINAL INPUT:
<<<
{raw_input}
>>>

EXTRACTED DOCUMENT:
{doc_json}

Check specifically:
1. Are ALL actors present (human, external systems, scheduled jobs, admins)?
2. Are ALL functional workflows covered (CRUD, business rules, notifications, reporting, auth, error handling)?
3. Does every functional requirement have ≥1 Given/When/Then acceptance criterion?
4. Are ALL NFR categories represented with measurable metrics (with units)?
5. Is every actor used by ≥1 functional requirement?

Return the COMPLETE, corrected document. Preserve existing IDs. If nothing is missing, return the document unchanged.
"""

REFINE_PROMPT = """The requirements document failed validation. Fix the specific issues and return the COMPLETE corrected document.

CURRENT DOCUMENT:
{doc_json}

VALIDATION ERRORS:
{errors}

Rules for fixing:
- Do NOT remove requirements that already pass.
- Preserve all existing IDs; only add or minimally edit.
- Ensure every actor is used, every NFR has measurable metrics with units, and mandatory categories ({required_nfrs}) are present.
"""

# ---------- Nodes ----------
async def extract_node(state: RequirementsState) -> dict:
    client = get_instructor()
    doc: RequirementsDocument = await client.chat.completions.create(
        model=MODEL_DESIGN,
        response_model=RequirementsDocument,
        messages=[{"role": "user", "content": EXTRACT_PROMPT.format(raw_input=state.raw_input)}],
        max_retries=3,
    )
    return {"doc": doc}

async def audit_node(state: RequirementsState) -> dict:
    client = get_instructor()
    doc: RequirementsDocument = await client.chat.completions.create(
        model=MODEL_DESIGN,
        response_model=RequirementsDocument,
        messages=[{
            "role": "user",
            "content": AUDIT_PROMPT.format(
                raw_input=state.raw_input,
                doc_json=state.doc.model_dump_json(indent=2),
            ),
        }],
        max_retries=3,
    )
    return {"doc": doc}

async def validate_node(state: RequirementsState) -> dict:
    assert state.doc is not None
    errors = validate_requirements(state.doc)
    best_doc, best_count = state.best_doc, state.best_error_count
    if len(errors) < best_count:
        best_doc, best_count = state.doc, len(errors)
    return {"errors": errors, "best_doc": best_doc, "best_error_count": best_count}

async def refine_node(state: RequirementsState) -> dict:
    client = get_instructor()
    doc: RequirementsDocument = await client.chat.completions.create(
        model=MODEL_DESIGN,
        response_model=RequirementsDocument,
        messages=[{
            "role": "user",
            "content": REFINE_PROMPT.format(
                doc_json=state.doc.model_dump_json(indent=2),
                errors="\n".join(f"- {e}" for e in state.errors),
                required_nfrs="performance, security, reliability",
            ),
        }],
        max_retries=3,
    )
    return {"doc": doc, "iteration": state.iteration + 1}

async def finalize_node(state: RequirementsState) -> dict:
    final = state.best_doc or state.doc
    final_errors = validate_requirements(final) if final else ["No document produced."]
    return {"doc": final, "errors": final_errors, "done": True}

# ---------- Routing ----------
def route_after_validate(state: RequirementsState) -> str:
    if not state.errors:
        return "finalize"
    if state.iteration >= state.max_iterations:
        return "finalize"
    return "refine"

# ---------- Builder ----------
class RequirementsGraph:
    def __init__(self) -> None:
        g = StateGraph(RequirementsState)
        g.add_node("extract",  extract_node)
        g.add_node("audit",    audit_node)
        g.add_node("validate", validate_node)
        g.add_node("refine",   refine_node)
        g.add_node("finalize", finalize_node)

        g.set_entry_point("extract")
        g.add_edge("extract",  "audit")
        g.add_edge("audit",    "validate")
        g.add_conditional_edges(
            "validate",
            route_after_validate,
            {"refine": "refine", "finalize": "finalize"},
        )
        g.add_edge("refine",   "validate")
        g.add_edge("finalize", END)
        self.graph = g.compile()

    async def run(self, raw_input: str, max_iterations: int = 4) -> RequirementsState:
        result = await self.graph.ainvoke({
            "raw_input": raw_input,
            "max_iterations": max_iterations,
        })
        return RequirementsState.model_validate(result)


# Independent usage
if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    raw = Path("src/input/requirements.txt").read_text()
    state = asyncio.run(RequirementsGraph().run(raw))

    print(f"Iterations: {state.iteration}")
    print(f"Errors: {len(state.errors)}")
    for e in state.errors:
        print("  -", e)

    if state.doc:
        Path("src/input/requirements.json").write_text(state.doc.model_dump_json(indent=2))
        print(f"\nSaved: src/input/requirements.json")
        print(f"  actors:       {len(state.doc.actors)}")
        print(f"  functional:   {len(state.doc.functional)}")
        print(f"  non_functional: {len(state.doc.non_functional)}")