from backend.app.ai.pipeline import AnalysisPipeline
from backend.app.ai.service import AIAnalysisService


def make_service():
    def save_entities(evidence_id, entities):
        pass

    def save_flags(evidence_id, flags):
        pass

    def update_status(evidence_id, status):
        pass

    pipeline = AnalysisPipeline(
        save_entities=save_entities,
        save_flags=save_flags,
        update_status=update_status,
    )

    return AIAnalysisService(pipeline)


def test_service_analyse():
    service = make_service()

    result = service.analyse(
        evidence_id="ev-001",
        text="Contact test@example.com",
    )

    assert result["status"] == "done"
    assert result["evidence_id"] == "ev-001"
    assert result["entities"][0]["type"] == "email"


def test_service_detects_threat():
    service = make_service()

    result = service.analyse(
        evidence_id="ev-002",
        text="I will kill you tonight.",
    )

    assert result["status"] == "done"
    assert len(result["flags"]) == 1
    assert result["flags"][0]["category"] == "violence_threat"