from backend.app.ai import AIAnalysisService
from backend.app.ai.pipeline import AnalysisPipeline


def test_ai_public_service_import():
    def save_entities(evidence_id, entities):
        pass

    def save_flags(evidence_id, flags):
        pass

    def update_status(evidence_id, status):
        pass

    service = AIAnalysisService(
        AnalysisPipeline(
            save_entities=save_entities,
            save_flags=save_flags,
            update_status=update_status,
        )
    )

    result = service.analyse(
        evidence_id="ev-003",
        text="Email me at hello@example.com",
    )

    assert result["status"] == "done"