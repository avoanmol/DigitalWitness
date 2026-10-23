import unittest
from types import SimpleNamespace
from uuid import uuid4

from backend.access import can_access_case


class CaseAccessTests(unittest.TestCase):
    def setUp(self):
        self.owner_id = uuid4()
        self.other_id = uuid4()
        self.case = SimpleNamespace(created_by=self.owner_id)

    def test_creator_can_access_case(self):
        self.assertTrue(
            can_access_case(SimpleNamespace(id=self.owner_id, role="reporter"), self.case)
        )

    def test_admin_can_access_case(self):
        self.assertTrue(
            can_access_case(SimpleNamespace(id=self.other_id, role="admin"), self.case)
        )

    def test_unrelated_user_cannot_access_case(self):
        self.assertFalse(
            can_access_case(SimpleNamespace(id=self.other_id, role="reporter"), self.case)
        )


if __name__ == "__main__":
    unittest.main()
