"""Create a timestamped PostgreSQL dump and encrypted-object backup."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def docker_executable() -> str:
    configured = os.getenv("DW_DOCKER_COMMAND")
    if configured:
        return configured
    found = shutil.which("docker")
    if found:
        return found
    candidates = [
        Path(os.getenv("LOCALAPPDATA", "")) / "Programs/DockerDesktop/resources/bin/docker.exe",
        Path(os.getenv("ProgramFiles", "C:/Program Files")) / "Docker/Docker/resources/bin/docker.exe",
    ]
    return str(next((item for item in candidates if item.is_file()), "docker"))


def run(command: list[str], *, stdout=None) -> None:
    subprocess.run(command, cwd=ROOT, check=True, stdout=stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "backups")
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = args.output_dir.resolve() / stamp
    target.mkdir(parents=True, exist_ok=False)
    docker = docker_executable()
    pg_dump = target / "postgres.dump"
    with pg_dump.open("wb") as output:
        run([docker, "compose", "exec", "-T", "db", "sh", "-c", 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc'], stdout=output)
    container_archive = "/tmp/digitalwitness-objects-backup.tar.gz"
    run([docker, "compose", "exec", "-T", "api", "python", "-m", "backend.storage_backup", "backup", "--output", container_archive])
    run([docker, "compose", "cp", f"api:{container_archive}", str(target / "objects.tar.gz")])
    (target / "README.txt").write_text(
        "DigitalWitness local backup\n"
        "postgres.dump is a PostgreSQL custom-format backup.\n"
        "objects.tar.gz contains encrypted evidence objects plus size/hash checksums.\n"
        "Keep this directory private and store a separate copy of your .env secrets securely.\n",
        encoding="utf-8",
    )
    print(f"Backup created: {target}")


if __name__ == "__main__":
    main()
