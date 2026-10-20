import hashlib


def analysis_job_key(
    evidence_id: str,
    evidence_sha256: str,
) -> str:
    """
    Generate a deterministic key for an analysis job.

    Same evidence + same hash => same job key.
    """
    raw = f"analyse:{evidence_id}:{evidence_sha256}"

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def link_job_key(case_id: str) -> str:
    """Generate a deterministic key for a case-link job."""
    raw = f"link:{case_id}"

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()