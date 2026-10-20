# design/states.py
from pydantic import BaseModel, Field
from .common import TracedModel

class State(BaseModel):
    name: str
    entity_id: str          # which entity owns this state
    is_initial: bool = False
    is_terminal: bool = False

class Transition(BaseModel):
    id: str                 # TRN-001
    from_state: str
    to_state: str
    trigger: str            # method name or domain event that fires this
    guard: str | None = None
    derived_from: list[str] = []

class StateMachine(TracedModel):
    entity_id: str          # e.g. ENT-Order
    states: list[State] = Field(min_length=2)
    transitions: list[Transition] = Field(min_length=1)

class StateModel(BaseModel):
    machines: list[StateMachine] = []