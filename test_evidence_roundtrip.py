
import hashlib

from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import Evidence
from backend.storage import get_encrypted_evidence
from backend.security import decrypt_evidence


def main():
    with SessionLocal() as db:
        evidence = db.scalar(
            select(Evidence)
            .where(Evidence.status == "stored")
            .order_by(Evidence.uploaded_at.desc())
            .limit(1)
        )

        if evidence is None:
            print("FAIL: No stored evidence record found.")
            return

        print("Evidence ID:", evidence.id)
        print("Filename:", evidence.original_filename)

        stored_data = get_encrypted_evidence(evidence.storage_key)

        if len(stored_data) < 13:
            print("FAIL: Stored object is too short.")
            return

        nonce = stored_data[:12]
        ciphertext = stored_data[12:]

        original_bytes = decrypt_evidence(ciphertext, nonce)
        actual_hash = hashlib.sha256(original_bytes).hexdigest()

        print("Decryption successful:", True)
        print("Original size matches:", len(original_bytes) == evidence.size_bytes)
        print("SHA-256 matches:", actual_hash == evidence.sha256)

        if (
            len(original_bytes) == evidence.size_bytes
            and actual_hash == evidence.sha256
        ):
            print("PASS: Evidence round-trip verification succeeded.")
        else:
            print("FAIL: Evidence integrity verification failed.")


if __name__ == "__main__":
    main()
