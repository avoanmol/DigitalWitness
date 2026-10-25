from typing import Any


class LLMClient:
    """Small interface for communicating with the hosted LLM."""

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def analyse(self, text: str) -> dict[str, Any]:
        """
        Analyse evidence text with the LLM.

        The actual provider/API call will be added after the
        team chooses the LLM provider.
        """
        if not self.enabled:
            return {
                "entities": [],
                "threats": [],
            }

        raise NotImplementedError(
            "LLM provider integration has not been configured yet."
        )