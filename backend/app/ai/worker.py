from __future__ import annotations
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy import select, text
from backend.app.ai.service import analyse_evidence, link_case
from backend.database import SessionLocal, engine
from backend.models import Analysis, Evidence, Job

logger = logging.getLogger("digitalwitness.ai_worker")
_LOCK_ID = 0x445741494A4F4253
_LEASE_SECONDS = 180

def _poll_seconds() -> float:
    try:
        value = float(os.getenv("AI_WORKER_POLL_SECONDS", "3"))
    except ValueError as exc:
        raise RuntimeError("AI_WORKER_POLL_SECONDS must be numeric") from exc
    if value <= 0:
        raise RuntimeError("AI_WORKER_POLL_SECONDS must be positive")
    return value

def _mark_evidence(db, payload: dict, status_value: str) -> None:
    evidence_id = payload.get("evidence_id")
    if not evidence_id:
        return
    try:
        evidence = db.get(Evidence, UUID(str(evidence_id)))
    except (ValueError, TypeError):
        return
    if evidence is not None:
        evidence.analysis_status = status_value
        analysis = db.scalar(select(Analysis).where(Analysis.evidence_id == evidence.id))
        if analysis is not None and status_value in {"pending", "running", "failed"}:
            analysis.status = status_value

def _claim_job() -> tuple[str, str, dict, int, int] | None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        expired = db.scalars(select(Job).where(Job.status == "running", Job.run_after <= now).with_for_update(skip_locked=True)).all()
        for job in expired:
            if job.attempts >= job.max_attempts:
                job.status = "failed"
                job.finished_at = now
                job.last_error = "AI job lease expired after the final attempt."
                _mark_evidence(db, job.payload or {}, "failed")
            else:
                job.status = "queued"
                job.run_after = now
                job.last_error = "Previous AI worker lease expired; queued for retry."
                _mark_evidence(db, job.payload or {}, "pending")
        job = db.scalar(select(Job).where(Job.status == "queued", Job.run_after <= now).order_by(Job.created_at, Job.id).with_for_update(skip_locked=True).limit(1))
        if job is None:
            db.commit()
            return None
        job.status = "running"
        job.attempts += 1
        job.run_after = now + timedelta(seconds=_LEASE_SECONDS)
        job.last_error = None
        if job.type == "analyse":
            _mark_evidence(db, job.payload or {}, "running")
        result = (str(job.id), job.type, dict(job.payload or {}), job.attempts, job.max_attempts)
        db.commit()
        return result

def _finish_job(job_id: str, *, error_type: str | None, attempts: int, max_attempts: int, payload: dict, job_type: str) -> None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        job = db.get(Job, UUID(job_id))
        if job is None or job.status != "running":
            return
        if error_type is None:
            job.status = "done"
            job.finished_at = now
            job.last_error = None
        elif attempts >= max_attempts:
            job.status = "failed"
            job.finished_at = now
            job.last_error = f"{error_type}: analysis job failed after retries."
            if job_type == "analyse":
                _mark_evidence(db, payload, "failed")
        else:
            job.status = "queued"
            job.run_after = now + timedelta(seconds=min(300, 5 * (2 ** (attempts - 1))))
            job.last_error = f"{error_type}: analysis job will retry."
            if job_type == "analyse":
                _mark_evidence(db, payload, "pending")
        db.commit()

def process_one_job() -> bool:
    claimed = _claim_job()
    if claimed is None:
        return False
    job_id, job_type, payload, attempts, max_attempts = claimed
    error_type = None
    try:
        if job_type == "analyse":
            analyse_evidence(str(payload["evidence_id"]), SessionLocal)
        elif job_type == "link":
            link_case(str(payload["case_id"]), SessionLocal)
        else:
            raise ValueError("Unknown AI job type")
    except Exception as exc:
        error_type = type(exc).__name__
        logger.warning("AI job %s (%s) failed on attempt %d with %s", job_id, job_type, attempts, error_type)
    _finish_job(job_id, error_type=error_type, attempts=attempts, max_attempts=max_attempts, payload=payload, job_type=job_type)
    return True

def run_forever() -> None:
    poll = _poll_seconds()
    with engine.connect() as lock_connection:
        acquired = bool(lock_connection.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": _LOCK_ID}).scalar_one())
        lock_connection.commit()
        if not acquired:
            raise RuntimeError("another AI worker already holds the worker lock")
        logger.info("AI worker started; polling every %.1f seconds", poll)
        try:
            while True:
                try:
                    processed = process_one_job()
                except Exception as exc:
                    logger.warning("AI worker polling failed (%s)", type(exc).__name__)
                    processed = False
                time.sleep(.25 if processed else poll)
        finally:
            lock_connection.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": _LOCK_ID})
            lock_connection.commit()

def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    run_forever()

if __name__ == "__main__":
    main()
