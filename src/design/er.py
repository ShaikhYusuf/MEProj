# design/er.py
from typing import Literal
from pydantic import BaseModel, Field
from .common import TracedModel

class Attribute(BaseModel):
    name: str
    type: str
    nullable: bool = False
    unique: bool = False
    primary_key: bool = False

class Entity(TracedModel):
    name: str
    attributes: list[Attribute] = Field(min_length=1)

class Relation(BaseModel):
    from_entity: str
    to_entity: str
    cardinality: Literal["1:1", "1:N", "N:1", "N:M"]
    label: str

class ERModel(BaseModel):
    entities: list[Entity] = Field(min_length=1)
    relations: list[Relation] = []
