from uuid import uuid4

from backend.app.api.analysis import (
    FlagReviewRequest,
    LinkReviewRequest,
    ManualLinkRequest,
)


def test_flag_review_request():
    request = FlagReviewRequest(
        review_status="confirmed"
    )

    assert request.review_status == "confirmed"


def test_link_review_request():
    request = LinkReviewRequest(
        status="rejected"
    )

    assert request.status == "rejected"


def test_manual_link_request():
    case_a = uuid4()
    case_b = uuid4()

    request = ManualLinkRequest(
        case_a_id=case_a,
        case_b_id=case_b,
        note="Shared phone number",
    )

    assert request.case_a_id == case_a
    assert request.case_b_id == case_b
    assert request.note == "Shared phone number"