# design/objects.py
from pydantic import BaseModel, Field
from .common import TracedModel

class Param(BaseModel):
    name: str
    type: str                 # Python type annotation, e.g. "UUID", "list[Item]"
    optional: bool = False

class PublicMethod(TracedModel):
    name: str
    params: list[Param] = []
    returns: str              # "None", "Order", "list[Item]", etc.
    serves_steps: list[str] = []   # UC-003-S01 IDs this method implements
    description: str = ""

class Object(TracedModel):
    name: str                 # e.g. OrderService
    protocol_name: str        # e.g. OrderServiceProtocol
    responsibility: str       # one-sentence purpose
    entity_refs: list[str] = []    # ENT-* this object owns
    methods: list[PublicMethod] = Field(min_length=1)

class ObjectModel(BaseModel):
    objects: list[Object] = Field(min_length=1)