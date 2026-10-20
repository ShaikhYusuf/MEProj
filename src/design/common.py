# design/common.py
from typing import Literal
from pydantic import BaseModel, Field

class TracedModel(BaseModel):
    id: str = Field(..., description="Stable ID, e.g. REQ-001, ENT-Customer, OBJ-OrderService")
    derived_from: list[str] = Field(default_factory=list, description="IDs of upstream artifacts")
    status: Literal["draft", "approved", "deprecated"] = "draft"

    