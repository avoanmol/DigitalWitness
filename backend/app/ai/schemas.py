from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

EntityType = Literal["handle", "phone", "email", "url"]
Severity = Literal["low", "medium", "high", "critical"]
ThreatClass = Literal[
    "cyberstalking_bullying", "blackmail_threatening", "intimate_image_abuse",
    "defamation_morphing", "fake_profile_impersonation", "other",
]

class LLMEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: EntityType
    value: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0, le=1)

class LLMThreat(BaseModel):
    model_config = ConfigDict(extra="ignore")
    threat_class: ThreatClass
    severity: Severity
    snippet: str = Field(min_length=1, max_length=4000)
    confidence: float = Field(ge=0, le=1)
    reason: str | None = Field(default=None, max_length=1000)

class LLMResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    text: str = Field(default="", max_length=100000)
    language: str | None = Field(default=None, max_length=20)
    entities: list[LLMEntity] = Field(default_factory=list, max_length=200)
    threats: list[LLMThreat] = Field(default_factory=list, max_length=100)

class FlagReviewRequest(BaseModel):
    review_status: Literal["confirmed", "rejected"]
    review_reason: Literal[
        "source_supports_flag",
        "reported_or_quoted_context",
        "educational_or_hypothetical_context",
        "wrong_category",
        "snippet_not_supported",
        "extraction_unclear",
        "duplicate_or_repeated",
        "insufficient_context",
        "other",
    ]

class LinkReviewRequest(BaseModel):
    status: Literal["confirmed", "rejected"]
    review_reason: Literal[
        "source_supports_connection",
        "shared_identifier_is_common",
        "different_account_or_person",
        "separate_context",
        "insufficient_context",
        "other",
    ]

class LinkCreateRequest(BaseModel):
    case_a_id: UUID
    case_b_id: UUID
    note: str = Field(default="", max_length=1000)
