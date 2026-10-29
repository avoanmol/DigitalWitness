import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.storage_backup import backup_objects, restore_objects


class MissingObject(Exception):
    response = {"Error": {"Code": "404"}}


class FakePaginator:
    def __init__(self, objects):
        self.objects = objects

    def paginate(self, **_kwargs):
        yield {"Contents": [{"Key": key, "Size": len(value)} for key, value in self.objects.items()]}


class FakeS3:
    def __init__(self):
        self.objects = {"cases/demo/evidence/one": b"encrypted sample", "cases/demo/evidence/two": b"more encrypted bytes"}

    def get_paginator(self, _name):
        return FakePaginator(self.objects)

    def get_object(self, *, Key, **_kwargs):
        return {"Body": io.BytesIO(self.objects[Key])}

    def head_object(self, *, Key, **_kwargs):
        if Key not in self.objects:
            raise MissingObject()
        return {}

    def upload_fileobj(self, body, _bucket, key, **_kwargs):
        self.objects[key] = body.read()


class StorageBackupTests(unittest.TestCase):
    def test_archive_checksums_and_restore_refuses_overwrite(self):
        client = FakeS3()
        expected = dict(client.objects)
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "objects.tar.gz"
            with patch("backend.storage_backup.get_s3_client", return_value=client):
                result = backup_objects(archive)
                self.assertEqual(result["object_count"], 2)

                client.objects.clear()
                self.assertEqual(restore_objects(archive)["restored"], 2)
                self.assertEqual(client.objects, expected)
                with self.assertRaises(FileExistsError):
                    restore_objects(archive)
                self.assertEqual(restore_objects(archive, allow_overwrite=True)["restored"], 2)


if __name__ == "__main__":
    unittest.main()
