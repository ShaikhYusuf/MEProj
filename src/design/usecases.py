# design/usecases.py
from pydantic import BaseModel, Field
from .common import TracedModel

class Step(BaseModel):
    id: str                        # UC-003-S01
    order: int
    description: str
    actor_id: str | None = None    # None = the system itself
    entity_refs: list[str] = []    # ENT-* touched by this step

class UseCase(TracedModel):
    name: str
    primary_actor_id: str
    supporting_actor_ids: list[str] = []
    preconditions: list[str] = []
    postconditions: list[str] = []
    steps: list[Step] = Field(min_length=1)

class UseCaseModel(BaseModel):
    usecases: list[UseCase] = Field(min_length=1)