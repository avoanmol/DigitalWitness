"""Stream encrypted evidence objects to/from a checksummed archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import tarfile
from pathlib import Path, PurePosixPath

from backend.storage import get_s3_client


ARCHIVE_VERSION = 1


def backup_objects(output: Path) -> dict:
    client = get_s3_client()
    bucket = os.getenv("MINIO_BUCKET", "evidence")
    paginator = client.get_paginator("list_objects_v2")
    records: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="dw-storage-backup-") as temp_dir:
        temp = Path(temp_dir)
        with tarfile.open(output, "w:gz") as archive:
            index = 0
            for page in paginator.paginate(Bucket=bucket):
                for item in page.get("Contents", []):
                    key = item["Key"]
                    response = client.get_object(Bucket=bucket, Key=key)
                    body = response["Body"]
                    local = temp / str(index)
                    digest = hashlib.sha256()
                    size = 0
                    try:
                        with local.open("wb") as stream:
                            while chunk := body.read(1024 * 1024):
                                stream.write(chunk)
                                digest.update(chunk)
                                size += len(chunk)
                    finally:
                        body.close()
                    arcname = f"objects/{index}"
                    archive.add(local, arcname=arcname, recursive=False)
                    records.append({"key": key, "path": arcname, "size_bytes": size, "sha256": digest.hexdigest()})
                    index += 1
            manifest = {"version": ARCHIVE_VERSION, "bucket": bucket, "objects": records}
            manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
            from io import BytesIO
            info = tarfile.TarInfo("manifest.json")
            info.size = len(manifest_bytes)
            archive.addfile(info, BytesIO(manifest_bytes))
    return {"bucket": bucket, "object_count": len(records), "archive": str(output)}


def restore_objects(source: Path, *, allow_overwrite: bool = False) -> dict:
    client = get_s3_client()
    with tarfile.open(source, "r:gz") as archive:
        manifest_member = archive.getmember("manifest.json")
        if manifest_member.size > 16 * 1024 * 1024:
            raise ValueError("Object archive manifest is too large.")
        manifest_stream = archive.extractfile(manifest_member)
        if manifest_stream is None:
            raise ValueError("Object archive is missing its manifest.")
        manifest = json.loads(manifest_stream.read().decode("utf-8"))
        if manifest.get("version") != ARCHIVE_VERSION:
            raise ValueError("Unsupported object archive version.")
        bucket = os.getenv("MINIO_BUCKET", "evidence")
        if manifest.get("bucket") != bucket:
            raise ValueError("Backup bucket name does not match the configured evidence bucket.")
        restored = 0
        with tempfile.TemporaryDirectory(prefix="dw-storage-restore-") as temp_dir:
            temp = Path(temp_dir)
            for entry in manifest.get("objects", []):
                key = entry.get("key")
                arcname = entry.get("path")
                if not isinstance(key, str) or not key or not isinstance(arcname, str):
                    raise ValueError("Object archive has an invalid object record.")
                path = PurePosixPath(arcname)
                if path.is_absolute() or path.parts[0:1] != ("objects",) or len(path.parts) != 2:
                    raise ValueError("Object archive contains an unsafe member path.")
                if not path.parts[1].isdigit():
                    raise ValueError("Object archive contains an invalid object index.")
                member = archive.getmember(arcname)
                if not member.isfile():
                    raise ValueError("Object archive entries must be regular files.")
                if member.size != entry.get("size_bytes"):
                    raise ValueError(f"Size mismatch in backup object {key}.")
                try:
                    client.head_object(Bucket=bucket, Key=key)
                    exists = True
                except Exception as exc:
                    code = getattr(exc, "response", {}).get("Error", {}).get("Code")
                    if code not in {"404", "NoSuchKey", "NotFound"}:
                        raise
                    exists = False
                if exists and not allow_overwrite:
                    raise FileExistsError(f"Object already exists: {key}. Re-run with --allow-overwrite after confirming the target.")
                source_stream = archive.extractfile(member)
                if source_stream is None:
                    raise ValueError(f"Backup archive is missing object data: {key}.")
                local = temp / path.parts[1]
                digest = hashlib.sha256()
                with local.open("wb") as output:
                    while chunk := source_stream.read(1024 * 1024):
                        output.write(chunk)
                        digest.update(chunk)
                if digest.hexdigest() != entry.get("sha256"):
                    raise ValueError(f"Checksum mismatch in backup object {key}.")
                with local.open("rb") as body:
                    client.upload_fileobj(body, bucket, key, ExtraArgs={"ContentType": "application/octet-stream"})
                restored += 1
    return {"restored": restored, "bucket": os.getenv("MINIO_BUCKET", "evidence")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    backup = subparsers.add_parser("backup")
    backup.add_argument("--output", required=True, type=Path)
    restore = subparsers.add_parser("restore")
    restore.add_argument("--input", required=True, type=Path)
    restore.add_argument("--allow-overwrite", action="store_true")
    args = parser.parse_args()
    result = backup_objects(args.output) if args.command == "backup" else restore_objects(args.input, allow_overwrite=args.allow_overwrite)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
