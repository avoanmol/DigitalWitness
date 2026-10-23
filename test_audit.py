
from sqlalchemy import select

from backend.audit import append_audit_event, verify_audit_chain
from backend.database import SessionLocal
from backend.models import AuditLog


def main():
    with SessionLocal() as db:
        try:
            event = append_audit_event(
                db,
                action="test.audit",
                target_type="system",
                details={"purpose": "temporary audit helper test"},
            )
            db.flush()

            stored = db.scalar(
                select(AuditLog).where(AuditLog.id == event.id)
            )

            assert stored is not None
            assert len(stored.prev_hash) == 64
            assert len(stored.entry_hash) == 64

            result = verify_audit_chain(db)

            print("Audit event creation: PASS")
            print("Hash format: PASS")
            print("Audit chain valid:", result["valid"])
            print("Entries checked:", result["entries_checked"])

            assert result["valid"], result["reason"]

        finally:
            db.rollback()


if __name__ == "__main__":
    main()
