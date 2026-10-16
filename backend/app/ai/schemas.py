from pydantic import BaseModel, Field


class Entity(BaseModel):
    type: str
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    snippet: str


class ThreatFlag(BaseModel):
    category: str
    severity: str
    confidence: float = Field(ge=0.0, le=1.0)
    snippet: str


class AnalysisResult(BaseModel):
    entities: list[Entity] = Field(default_factory=list)
    threats: list[ThreatFlag] = Field(default_factory=list)