from typing import Any

from .pipeline import AnalysisPipeline
from .pipeline_result import failed_result


class AIAnalysisService:
    """
    Public service layer for the backend.

    B's API/worker code can call this service without needing
    to know how entity extraction or threat detection works.
    """

    def __init__(
        self,
        pipeline: AnalysisPipeline,
    ) -> None:
        self.pipeline = pipeline

    def analyse(
        self,
        evidence_id: str,
        text: str,
    ) -> dict[str, Any]:
        try:
            return self.pipeline.analyse(
                evidence_id=evidence_id,
                text=text,
            )
        except Exception:
            return failed_result(evidence_id)