# design/sequence.py
from pydantic import BaseModel, Field
from .common import TracedModel

class Message(BaseModel):
    order: int
    from_id: str            # ACT-* or OBJ-* (object name, not ID)
    to_id: str              # OBJ-* (object name)
    method: str
    args: list[str] = []    # argument expressions as strings, e.g. "customer_id"
    returns: str | None = None   # e.g. "order"

class Sequence(TracedModel):
    name: str
    messages: list[Message] = Field(min_length=1)

class SequenceModel(BaseModel):
    sequences: list[Sequence] = Field(min_length=1)