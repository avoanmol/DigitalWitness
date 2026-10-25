from typing import Any


class IdempotencyStore:
    """
    Small in-memory store used to prevent the same job from
    producing duplicate results.

    B's database-backed implementation can replace this later.
    """

    def __init__(self) -> None:
        self._completed: dict[str, Any] = {}

    def has_completed(self, job_key: str) -> bool:
        return job_key in self._completed

    def get(self, job_key: str) -> Any:
        return self._completed.get(job_key)

    def save(
        self,
        job_key: str,
        result: Any,
    ) -> None:
        self._completed[job_key] = result

    def clear(self, job_key: str) -> None:
        self._completed.pop(job_key, None)