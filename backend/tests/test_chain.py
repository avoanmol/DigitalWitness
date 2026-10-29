import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.integrity.chain import (
    ChainError,
    ROOT_ANCHORED_TOPIC,
    anchor_root,
    get_batch,
    submit_root,
)


class ChainTests(unittest.TestCase):
    def setUp(self):
        self.root = "0x" + "45" * 32
        self.transaction_hash = "0x" + "99" * 32
        self.receipt = {
            "status": "0x1",
            "blockHash": "0x" + "aa" * 32,
            "blockNumber": "0xa",
            "logs": [
                {
                    "address": "0x" + "11" * 20,
                    "topics": [
                        ROOT_ANCHORED_TOPIC,
                        "0x" + format(5, "064x"),
                    ],
                    "data": (
                        self.root
                        + format(4, "064x")
                        + format(123, "064x")
                    ),
                }
            ],
        }

    def test_anchor_reads_chain_batch_id_from_event_and_returns_block(self):
        environment = {
            "CHAIN_RPC_URL": "http://127.0.0.1:8545",
            "CHAIN_CONTRACT_ADDRESS": "0x" + "11" * 20,
            "CHAIN_SENDER_ADDRESS": "0x" + "22" * 20,
            "CHAIN_PRIVATE_KEY": "",
            "CHAIN_CONFIRMATIONS": "1",
            "CHAIN_EXPECTED_ID": "31337",
        }
        with patch.dict(os.environ, environment, clear=False):
            with patch("app.integrity.chain._rpc") as rpc:
                rpc.side_effect = [
                    "0x7a69",
                    self.transaction_hash,
                    "0x7a69",
                    self.receipt,
                    "0xa",
                    {"hash": self.receipt["blockHash"]},
                    self.receipt,
                ]
                result = anchor_root(self.root, 4)

        self.assertEqual(result["transaction_hash"], self.transaction_hash)
        self.assertEqual(result["chain_batch_id"], 5)
        self.assertEqual(result["block_number"], 10)
        self.assertEqual(result["chain_id"], 31337)

    def test_submit_returns_transaction_hash_before_receipt_polling(self):
        environment = {
            "CHAIN_RPC_URL": "http://127.0.0.1:8545",
            "CHAIN_CONTRACT_ADDRESS": "0x" + "11" * 20,
            "CHAIN_SENDER_ADDRESS": "0x" + "22" * 20,
            "CHAIN_PRIVATE_KEY": "",
            "CHAIN_EXPECTED_ID": "31337",
        }
        with patch.dict(os.environ, environment, clear=False):
            with patch("app.integrity.chain._rpc") as rpc:
                rpc.side_effect = ["0x7a69", self.transaction_hash]
                result = submit_root(self.root, 4)

        self.assertEqual(result["transaction_hash"], self.transaction_hash)
        self.assertEqual(result["chain_id"], 31337)
        self.assertEqual(rpc.call_count, 2)
        self.assertEqual(rpc.call_args_list[-1].args[0], "eth_sendTransaction")

    def test_submit_rejects_unexpected_chain_before_broadcast(self):
        environment = {
            "CHAIN_RPC_URL": "https://polygon-amoy.example/rpc",
            "CHAIN_CONTRACT_ADDRESS": "0x" + "11" * 20,
        }
        with patch.dict(os.environ, environment, clear=True):
            with patch("app.integrity.chain._rpc", return_value="0x7a69") as rpc:
                with self.assertRaisesRegex(ChainError, "CHAIN_EXPECTED_ID 80002"):
                    submit_root(self.root, 4)

        rpc.assert_called_once_with("eth_chainId", [])

    def test_reads_do_not_require_a_sender_address(self):
        environment = {
            "CHAIN_RPC_URL": "http://127.0.0.1:8545",
            "CHAIN_CONTRACT_ADDRESS": "0x" + "11" * 20,
            "CHAIN_SENDER_ADDRESS": "",
        }
        response = "0x" + "45" * 32 + format(4, "064x") + format(123, "064x")
        with patch.dict(os.environ, environment, clear=False):
            with patch("app.integrity.chain._rpc", return_value=response):
                result = get_batch(1)

        self.assertEqual(result["root"], self.root)
        self.assertEqual(result["leaf_count"], 4)

    def test_rejects_empty_root_before_rpc(self):
        with patch("app.integrity.chain._rpc") as rpc:
            with self.assertRaisesRegex(ValueError, "empty"):
                anchor_root("0x" + "00" * 32, 1)
        rpc.assert_not_called()


if __name__ == "__main__":
    unittest.main()
