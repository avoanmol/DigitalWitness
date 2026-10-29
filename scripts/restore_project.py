"""Restore a local backup. Database replacement requires an explicit flag and prompt."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from backup_project import docker_executable


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, stdin=None) -> None:
    subprocess.run(command, cwd=ROOT, check=True, stdin=stdin)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup_dir", type=Path)
    parser.add_argument("--confirm-database-replace", action="store_true")
    parser.add_argument("--allow-object-overwrite", action="store_true")
    args = parser.parse_args()
    backup = args.backup_dir.resolve()
    db_dump = backup / "postgres.dump"
    objects = backup / "objects.tar.gz"
    if not db_dump.is_file() or not objects.is_file():
        parser.error("backup directory must contain postgres.dump and objects.tar.gz")
    if not args.confirm_database_replace:
        parser.error("restore can replace database contents; pass --confirm-database-replace after making a separate backup")
    confirmation = input("This replaces the current DigitalWitness database. Type REPLACE to continue: ")
    if confirmation != "REPLACE":
        raise SystemExit("Restore cancelled.")

    docker = docker_executable()
    container_objects = "/tmp/digitalwitness-objects-restore.tar.gz"
    run([docker, "compose", "cp", str(objects), f"api:{container_objects}"])
    with db_dump.open("rb") as dump_stream:
        run([docker, "compose", "exec", "-T", "db", "sh", "-c", 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --clean --if-exists --exit-on-error --single-transaction'], stdin=dump_stream)
    command = [docker, "compose", "exec", "-T", "api", "python", "-m", "backend.storage_backup", "restore", "--input", container_objects]
    if args.allow_object_overwrite:
        command.append("--allow-overwrite")
    run(command)
    print("Restore completed. Confirm API, object storage, workers, and chain settings before resuming submissions.")


if __name__ == "__main__":
    main()
