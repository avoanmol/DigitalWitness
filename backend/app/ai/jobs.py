from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.models import Job

ACTIVE_STATUSES = {"queued", "running"}

def _active_job_exists(db: Session, job_type: str, key: str, value: str) -> bool:
    active = db.scalars(select(Job).where(Job.type == job_type, Job.status.in_(ACTIVE_STATUSES))).all()
    return any(str((job.payload or {}).get(key, "")) == value for job in active)

def enqueue_analysis(db: Session, evidence_id: str) -> bool:
    if _active_job_exists(db, "analyse", "evidence_id", evidence_id):
        return False
    db.add(Job(type="analyse", payload={"evidence_id": evidence_id}, status="queued"))
    return True

def enqueue_linking(db: Session, case_id: str) -> bool:
    if _active_job_exists(db, "link", "case_id", case_id):
        return False
    db.add(Job(type="link", payload={"case_id": case_id}, status="queued"))
    return True
