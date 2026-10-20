import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.integrity.merkle import (
    build_levels,
    get_proof,
    leaf_hash,
    node_hash,
    root_from_proof,
    verify_proof,
)


class MerkleTests(unittest.TestCase):
    def setUp(self):
        self.hashes = [format(number, "064x") for number in range(1, 9)]

    def test_empty_input_rejected(self):
        with self.assertRaises(ValueError):
            build_levels([])

    def test_single_leaf(self):
        levels = build_levels(self.hashes[:1])
        self.assertEqual(levels[-1][0], leaf_hash(self.hashes[0]))
        self.assertEqual(get_proof(levels, 0), [])

    def test_two_leaves(self):
        levels = build_levels(self.hashes[:2])
        expected = node_hash(
            leaf_hash(self.hashes[0]),
            leaf_hash(self.hashes[1]),
        )
        self.assertEqual(levels[-1][0], expected)

    def test_odd_node_is_promoted_unchanged(self):
        levels = build_levels(self.hashes[:3])
        expected = node_hash(
            node_hash(leaf_hash(self.hashes[0]), leaf_hash(self.hashes[1])),
            leaf_hash(self.hashes[2]),
        )
        self.assertEqual(levels[-1][0], expected)

    def test_every_proof_verifies_for_required_tree_sizes(self):
        for leaf_count in (1, 2, 3, 4, 5, 7, 8):
            with self.subTest(leaf_count=leaf_count):
                hashes = self.hashes[:leaf_count]
                levels = build_levels(hashes)
                root = levels[-1][0].hex()
                for index, file_hash in enumerate(hashes):
                    proof = get_proof(levels, index)
                    self.assertTrue(verify_proof(file_hash, proof, root))
                    self.assertEqual(root_from_proof(file_hash, proof), root)

    def test_modified_file_hash_rejected(self):
        levels = build_levels(self.hashes[:4])
        proof = get_proof(levels, 0)
        root = levels[-1][0].hex()
        self.assertFalse(verify_proof(format(99, "064x"), proof, root))

    def test_modified_sibling_rejected(self):
        levels = build_levels(self.hashes[:4])
        proof = get_proof(levels, 0)
        proof[0]["hash"] = format(99, "064x")
        self.assertFalse(
            verify_proof(self.hashes[0], proof, levels[-1][0].hex())
        )

    def test_invalid_side_rejected(self):
        with self.assertRaises(ValueError):
            root_from_proof(
                self.hashes[0],
                [{"hash": self.hashes[1], "side": "inside"}],  # type: ignore
            )

    def test_order_changes_root(self):
        forward = build_levels(self.hashes[:3])[-1][0]
        reversed_order = build_levels(list(reversed(self.hashes[:3])))[-1][0]
        self.assertNotEqual(forward, reversed_order)


if __name__ == "__main__":
    unittest.main()
