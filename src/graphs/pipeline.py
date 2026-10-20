# graphs/pipeline.py
from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel, Field

from src.design.requirements import RequirementsDocument
from src.design.er import ERModel
from src.design.states import StateModel
from src.design.usecases import UseCaseModel
from src.design.objects import ObjectModel
from src.design.sequence import SequenceModel

from graphs.requirements import RequirementsGraph
from graphs.er import ERGraph
from graphs.states import StatesGraph
from graphs.usecases import UseCasesGraph
from graphs.objects import ObjectsGraph
from graphs.sequence import SequenceGraph
from src.codegen.protocols import generate_protocols

class PipelineState(BaseModel):
    raw_input: str
    requirements: RequirementsDocument | None = None
    er: ERModel | None = None
    states: StateModel | None = None
    usecases: UseCaseModel | None = None
    objects: ObjectModel | None = None
    sequences: SequenceModel | None = None
    stage_errors: dict[str, list[str]] = Field(default_factory=dict)
    stage_iterations: dict[str, int] = Field(default_factory=dict)

class Pipeline:
    def __init__(self) -> None:
        self.req  = RequirementsGraph(); self.er   = ERGraph()
        self.st   = StatesGraph();       self.uc   = UseCasesGraph()
        self.ob   = ObjectsGraph();      self.seq  = SequenceGraph()

    def _stop_if_errors(self, state: PipelineState, stage: str) -> bool:
        return bool(state.stage_errors.get(stage))

    async def run(self, raw_input: str) -> PipelineState:
        s = PipelineState(raw_input=raw_input)

        r = await self.req.run(raw_input)
        s.requirements = r.doc; s.stage_errors["requirements"] = r.errors
        s.stage_iterations["requirements"] = r.iteration
        if self._stop_if_errors(s, "requirements"): return s

        e = await self.er.run(s.requirements)
        s.er = e.model; s.stage_errors["er"] = e.errors
        s.stage_iterations["er"] = e.iteration
        if self._stop_if_errors(s, "er"): return s

        st = await self.st.run(s.requirements, s.er)
        s.states = st.model; s.stage_errors["states"] = st.errors
        s.stage_iterations["states"] = st.iteration
        if self._stop_if_errors(s, "states"): return s

        u = await self.uc.run(s.requirements, s.er)
        s.usecases = u.model; s.stage_errors["usecases"] = u.errors
        s.stage_iterations["usecases"] = u.iteration
        if self._stop_if_errors(s, "usecases"): return s

        o = await self.ob.run(s.requirements, s.er, s.usecases)
        s.objects = o.model; s.stage_errors["objects"] = o.errors
        s.stage_iterations["objects"] = o.iteration
        if self._stop_if_errors(s, "objects"): return s

        q = await self.seq.run(s.requirements, s.objects, s.usecases)
        s.sequences = q.model; s.stage_errors["sequence"] = q.errors
        s.stage_iterations["sequence"] = q.iteration
        if self._stop_if_errors(s, "sequence"): return s

        # Emit Protocol contracts — bridge to the code stage
        generate_protocols(s.objects, Path("app/contracts"))
        return s