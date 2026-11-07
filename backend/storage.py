
import os

import boto3
from botocore.client import Config


def get_s3_client():
    # Prefer Neon Object Storage's branch-scoped credentials when present;
    # Compose continues to use its explicit MinIO settings.
    endpoint = os.getenv("AWS_ENDPOINT_URL_S3") or os.getenv("MINIO_ENDPOINT", "localhost:9000")

    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"http://{endpoint}"

    access_key = os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv("MINIO_SECRET_KEY")

    if not access_key or not secret_key:
        raise RuntimeError(
            "Configure Neon AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY or MinIO MINIO_ACCESS_KEY/MINIO_SECRET_KEY."
        )

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        config=Config(signature_version="s3v4"),
    )


def _bucket_name() -> str:
    return os.getenv("MINIO_BUCKET", "evidence")


def ensure_bucket_exists():
    client = get_s3_client()
    bucket = _bucket_name()

    try:
        client.head_bucket(Bucket=bucket)
    except Exception as exc:
        error_code = getattr(exc, "response", {}).get(
            "Error", {}
        ).get("Code")

        if error_code not in {"404", "NoSuchBucket", "NotFound"} or os.getenv("AWS_ENDPOINT_URL_S3"):
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


def store_encrypted_evidence_fileobj(storage_key: str, encrypted_file) -> None:
    """Upload a seekable encrypted file using S3 multipart support when needed."""
    client = get_s3_client()
    bucket = ensure_bucket_exists()
    encrypted_file.seek(0)
    client.upload_fileobj(
        encrypted_file,
        bucket,
        storage_key,
        ExtraArgs={"ContentType": "application/octet-stream"},
    )

def get_encrypted_evidence(storage_key: str) -> bytes:
    """Retrieve encrypted evidence bytes from object storage."""
    client = get_s3_client()
    bucket = _bucket_name()

    response = client.get_object(
        Bucket=bucket,
        Key=storage_key,
    )

    body = response["Body"]
    try:
        return body.read()
    finally:
        body.close()


def delete_encrypted_evidence(storage_key: str) -> None:
    """Remove an uploaded object when its database transaction fails."""
    client = get_s3_client()
    bucket = _bucket_name()
    client.delete_object(Bucket=bucket, Key=storage_key)
