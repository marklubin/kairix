# Define data models first
from typing import Literal, Optional

from pydantic import BaseModel


class Unit(BaseModel):
    type: Literal["entity", "action", "attribute", "topic", "event"]
    short_description: str
    id: str


class Relation(BaseModel):
    u: Unit
    v: Unit
    relationship_descriptor: str


class Extraction(BaseModel):
    relationships: Optional[list[Relation]]
