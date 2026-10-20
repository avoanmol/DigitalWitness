from typing import Literal

from pydantic import BaseModel, Field


ThreatCategory = Literal[
    "violence_threat",
    "harassment_stalking",
    "extortion_blackmail",
    "hate_speech",
    "fraud_scam",
    "self_harm_risk",
]

ThreatSeverity = Literal[
    "critical",
    "high",
    "medium",
    "low",
]


class Entity(BaseModel):
    type: str
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    snippet: str


class ThreatFlag(BaseModel):
    category: ThreatCategory
    severity: ThreatSeverity
    confidence: float = Field(ge=0.0, le=1.0)
    snippet: str


class AnalysisResult(BaseModel):
    entities: list[Entity] = Field(default_factory=list)
    threats: list[ThreatFlag] = Field(default_factory=list)