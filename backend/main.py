
import hashlib
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

app = FastAPI(
    title="DigitalWitness API",
    description="Backend for secure digital evidence preservation.",
    version="0.1.0",
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {".jpg", ".jpeg", ".png", ".pdf"}


@app.get("/")
def home():
    return {"message": "Welcome to DigitalWitness"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/evidence/upload")
async def upload_evidence(file: UploadFile = File(...)):
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_TYPES:
        await file.close()
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload JPG, PNG, or PDF.",
        )

    sha256 = hashlib.sha256()
    total_size = 0

    try:
        while True:
            chunk = await file.read(1024 * 1024)

            if not chunk:
                break

            total_size += len(chunk)

            if total_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail="File too large. Maximum size is 10 MB.",
                )

            sha256.update(chunk)
    finally:
        await file.close()

    return {
        "message": "File processed successfully",
        "filename": filename,
        "size_bytes": total_size,
        "sha256": sha256.hexdigest(),
        "status": "processed",
    }
