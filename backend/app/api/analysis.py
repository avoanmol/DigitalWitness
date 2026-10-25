from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter(tags=["analysis"])


class FlagReviewRequest(BaseModel):
    review_status: Literal["confirmed", "rejected"]


class ManualLinkRequest(BaseModel):
    case_a_id: UUID
    case_b_id: UUID
    note: str | None = None


class LinkReviewRequest(BaseModel):
    status: Literal["confirmed", "rejected"]


class AnalyseResponse(BaseModel):
    evidence_id: UUID
    status: str


class AnalysisResponse(BaseModel):
    evidence_id: UUID
    status: str
    language: str | None = None
    text: str | None = None
    entities: list[dict] = Field(default_factory=list)
    flags: list[dict] = Field(default_factory=list)


class LinkResponse(BaseModel):
    id: UUID
    case_a_id: UUID
    case_b_id: UUID
    shared_entities: list[dict] = Field(default_factory=list)
    confidence: float
    status: str


@router.get(
    "/evidence/{evidence_id}/analysis",
    response_model=AnalysisResponse,
)
def get_analysis(evidence_id: UUID):
    """
    Return the latest AI analysis for an evidence item.

    Database/service wiring will be connected to B's backend
    models once those are available.
    """
    raise NotImplementedError


@router.post(
    "/evidence/{evidence_id}/analyse",
    response_model=AnalyseResponse,
)
def analyse_evidence(evidence_id: UUID):
    """
    Queue an analysis job for an evidence item.
    """
    raise NotImplementedError


@router.patch("/flags/{flag_id}")
def review_flag(
    flag_id: UUID,
    request: FlagReviewRequest,
):
    """
    Confirm or reject an AI threat flag.
    """
    raise NotImplementedError


@router.get(
    "/cases/{case_id}/links",
    response_model=list[LinkResponse],
)
def get_case_links(case_id: UUID):
    """
    Return suggested and confirmed links for a case.
    """
    raise NotImplementedError


@router.post(
    "/links",
    response_model=LinkResponse,
)
def create_manual_link(request: ManualLinkRequest):
    """
    Create a manual case link.
    """
    raise NotImplementedError


@router.patch("/links/{link_id}")
def review_link(
    link_id: UUID,
    request: LinkReviewRequest,
):
    """
    Confirm or reject a suggested case link.
    """
    raise NotImplementedError