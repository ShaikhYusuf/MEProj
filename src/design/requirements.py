# design/requirements.py
from typing import Literal
from pydantic import BaseModel, Field
from .common import TracedModel

class Actor(TracedModel):
    name: str
    description: str
    kind: Literal["human", "system", "external", "scheduled"]

class AcceptanceCriterion(BaseModel):
    id: str
    given: str
    when: str
    then: str

class FunctionalRequirement(TracedModel):
    title: str
    description: str
    actor_id: str
    acceptance_criteria: list[AcceptanceCriterion] = Field(min_length=1)
    priority: Literal["must", "should", "could", "wont"] = "must"

class NFRMetric(BaseModel):
    name: str
    value: float
    unit: str
    comparison: Literal["<=", ">=", "==", "<", ">"]

class NonFunctionalRequirement(TracedModel):
    category: Literal[
        "performance", "scalability", "security", "usability",
        "reliability", "maintainability", "portability", "compliance",
    ]
    description: str
    metrics: list[NFRMetric] = Field(min_length=1)

class RequirementsDocument(BaseModel):
    actors: list[Actor] = Field(min_length=1)
    functional: list[FunctionalRequirement] = Field(min_length=1)
    non_functional: list[NonFunctionalRequirement] = []
    assumptions: list[str] = []
    open_questions: list[str] = []