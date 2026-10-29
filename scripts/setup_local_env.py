"""Create a local .env with development secrets without overwriting an existing file."""

import base64
import secrets
from pathlib import Path


def main() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        raise SystemExit(f"{env_path} already exists; left it unchanged.")

    postgres_password = secrets.token_hex(24)
    minio_password = secrets.token_hex(24)
    values = {
        "POSTGRES_DB": "dw",
        "POSTGRES_USER": "dw",
        "POSTGRES_PASSWORD": postgres_password,
        "DATABASE_URL": (
            "postgresql+psycopg://dw:"
            f"{postgres_password}@localhost:5432/dw"
        ),
        "MINIO_ROOT_USER": "dwminio",
        "MINIO_ROOT_PASSWORD": minio_password,
        "JWT_SECRET": secrets.token_hex(32),
        "JWT_EXPIRE_MINUTES": "60",
        "MINIO_ENDPOINT": "localhost:9000",
        "MINIO_ACCESS_KEY": "dwminio",
        "MINIO_SECRET_KEY": minio_password,
        "MINIO_BUCKET": "evidence",
        "MAX_UPLOAD_MB": "100",
        "EVIDENCE_ENC_KEY": base64.b64encode(secrets.token_bytes(32)).decode("ascii"),
        "RECEIPT_HMAC_KEY": secrets.token_hex(32),
    }
    content = "# Local development secrets; do not commit this file.\n"
    content += "\n".join(f"{key}={value}" for key, value in values.items())
    content += "\n"

    # Exclusive create prevents replacing a file created concurrently.
    with env_path.open("x", encoding="utf-8", newline="\n") as env_file:
        env_file.write(content)

    print(f"Created {env_path} with fresh local secrets (values not displayed).")


if __name__ == "__main__":
    main()
