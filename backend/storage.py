
import os

import boto3
from botocore.client import Config


def get_s3_client():
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")

    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"http://{endpoint}"

    access_key = os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("MINIO_SECRET_KEY")

    if not access_key or not secret_key:
        raise RuntimeError(
            "MINIO_ACCESS_KEY and MINIO_SECRET_KEY must be configured."
        )

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket_exists():
    client = get_s3_client()
    bucket = os.getenv("MINIO_BUCKET", "evidence")

    try:
        client.head_bucket(Bucket=bucket)
    except Exception as exc:
        error_code = getattr(exc, "response", {}).get(
            "Error", {}
        ).get("Code")

        if error_code not in {"404", "NoSuchBucket", "NotFound"}:
            raise

        client.create_bucket(Bucket=bucket)

    return bucket


def store_encrypted_evidence(
    storage_key: str,
    encrypted_data: bytes,
) -> None:
    client = get_s3_client()
    bucket = ensure_bucket_exists()

    client.put_object(
        Bucket=bucket,
        Key=storage_key,
        Body=encrypted_data,
        ContentType="application/octet-stream",
    )

def get_encrypted_evidence(storage_key: str) -> bytes:
    """Retrieve encrypted evidence bytes from object storage."""
    client = get_s3_client()
    bucket = os.getenv("MINIO_BUCKET", "evidence")

    response = client.get_object(
        Bucket=bucket,
        Key=storage_key,
    )

    return response["Body"].read()


def delete_encrypted_evidence(storage_key: str) -> None:
    """Remove an uploaded object when its database transaction fails."""
    client = get_s3_client()
    bucket = os.getenv("MINIO_BUCKET", "evidence")
    client.delete_object(Bucket=bucket, Key=storage_key)
