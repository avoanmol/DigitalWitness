from __future__ import annotations

import json
import os
import time
from typing import Any, TypedDict
from urllib.request import Request, urlopen


ANCHOR_ROOT_SELECTOR = "0x74574eab"
GET_BATCH_SELECTOR = "0x5ac44282"
BATCH_COUNT_SELECTOR = "0x06f13056"
ROOT_ANCHORED_TOPIC = (
    "0x87a28429f4bbd1ba3d51cb9e71f50aa444b326bf263911d58f7b0709df673909"
)


class ChainError(RuntimeError):
    """Raised when a blockchain RPC operation fails."""


class AnchorReceipt(TypedDict):
    transaction_hash: str
    chain_batch_id: int
    block_number: int
    chain_id: int


def _connection() -> tuple[str, str]:
    rpc_url = os.environ.get("CHAIN_RPC_URL", "http://127.0.0.1:8545")
    contract = os.environ.get("CHAIN_CONTRACT_ADDRESS", "")

    if not contract.startswith("0x") or len(contract) != 42:
        raise ChainError("Set CHAIN_CONTRACT_ADDRESS to the deployed contract address")
    try:
        int(contract[2:], 16)
    except ValueError as exc:
        raise ChainError("CHAIN_CONTRACT_ADDRESS must be hexadecimal") from exc

    return rpc_url, contract.lower()


def _sender() -> str:
    sender = os.environ.get("CHAIN_SENDER_ADDRESS", "")
    if not sender.startswith("0x") or len(sender) != 42:
        raise ChainError("Set CHAIN_SENDER_ADDRESS to an unlocked node account")
    try:
        int(sender[2:], 16)
    except ValueError as exc:
        raise ChainError("CHAIN_SENDER_ADDRESS must be hexadecimal") from exc
    return sender.lower()


def _rpc(method: str, params: list[Any]) -> Any:
    rpc_url, _ = _connection()
    body = json.dumps(
        {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    ).encode("utf-8")
    request = Request(
        rpc_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except Exception:
        raise ChainError(f"RPC transport failed during {method}") from None

    if "error" in payload:
        raise ChainError(f"RPC request {method} failed: {payload['error']}")
    if "result" not in payload:
        raise ChainError(f"RPC response for {method} did not include a result")
    return payload["result"]


def _send_transaction(contract: str, calldata: str) -> str:
    private_key = os.environ.get("CHAIN_PRIVATE_KEY")
    if private_key:
        try:
            from web3 import Web3
        except Exception:
            raise ChainError(
                "Testnet signing needs web3.py in a runtime that permits its native modules"
            ) from None

        rpc_url, _ = _connection()
        web3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
        if not web3.is_connected():
            raise ChainError("Could not connect to the configured chain RPC")

        account = web3.eth.account.from_key(private_key)
        transaction: dict[str, Any] = {
            "from": account.address,
            "to": Web3.to_checksum_address(contract),
            "data": calldata,
            "nonce": web3.eth.get_transaction_count(account.address),
            "chainId": web3.eth.chain_id,
        }
        transaction["gas"] = web3.eth.estimate_gas(transaction)

        latest_block = web3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas")
        if base_fee is not None:
            priority_fee = web3.eth.max_priority_fee
            transaction["maxPriorityFeePerGas"] = priority_fee
            transaction["maxFeePerGas"] = 2 * base_fee + priority_fee
        else:
            transaction["gasPrice"] = web3.eth.gas_price

        signed = account.sign_transaction(transaction)
        return web3.eth.send_raw_transaction(signed.raw_transaction).hex()

    sender = _sender()
    return _rpc(
        "eth_sendTransaction",
        [{"from": sender, "to": contract, "data": calldata}],
    )


def _anchor_event(receipt: dict[str, Any], root: str, leaf_count: int) -> int:
    for log in receipt.get("logs", []):
        topics = log.get("topics", [])
        if not topics or topics[0].lower() != ROOT_ANCHORED_TOPIC:
            continue
        if len(topics) < 2:
            break

        data = log.get("data", "0x").removeprefix("0x")
        if len(data) < 192:
            break

        emitted_root = "0x" + data[0:64].lower()
        emitted_leaf_count = int(data[64:128], 16)
        if emitted_root != root.lower() or emitted_leaf_count != leaf_count:
            raise ChainError("RootAnchored event did not match the submitted batch")
        return int(topics[1], 16)

    raise ChainError("Anchor transaction receipt did not contain RootAnchored")


def _wait_for_receipt(
    transaction_hash: str,
    root: str,
    leaf_count: int,
    chain_id: int,
) -> AnchorReceipt:
    default_confirmations = 1 if chain_id == 31337 else 2
    try:
        confirmations = int(
            os.environ.get("CHAIN_CONFIRMATIONS", str(default_confirmations))
        )
    except ValueError as exc:
        raise ChainError("CHAIN_CONFIRMATIONS must be an integer") from exc
    if confirmations < 1:
        raise ChainError("CHAIN_CONFIRMATIONS must be at least 1")

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        receipt = _rpc("eth_getTransactionReceipt", [transaction_hash])
        if receipt is None:
            time.sleep(0.25)
            continue

        if int(receipt["status"], 16) != 1:
            raise ChainError(f"Anchor transaction reverted: {transaction_hash}")

        chain_batch_id = _anchor_event(receipt, root, leaf_count)
        block_number = int(receipt["blockNumber"], 16)

        while time.monotonic() < deadline:
            latest_block = int(_rpc("eth_blockNumber", []), 16)
            if latest_block >= block_number + confirmations - 1:
                return {
                    "transaction_hash": transaction_hash,
                    "chain_batch_id": chain_batch_id,
                    "block_number": block_number,
                    "chain_id": chain_id,
                }
            time.sleep(0.25)

        break

    raise ChainError(f"Timed out waiting for anchor confirmations: {transaction_hash}")


def get_batch_count() -> int:
    _, contract = _connection()
    result = _rpc(
        "eth_call",
        [{"to": contract, "data": BATCH_COUNT_SELECTOR}, "latest"],
    )
    return int(result, 16)


def get_batch(chain_batch_id: int) -> dict[str, int | str]:
    if not isinstance(chain_batch_id, int) or isinstance(chain_batch_id, bool):
        raise ValueError("chain_batch_id must be an integer")
    if not 1 <= chain_batch_id < 2**256:
        raise ValueError("chain_batch_id must be between 1 and 2**256 - 1")

    _, contract = _connection()
    calldata = GET_BATCH_SELECTOR + format(chain_batch_id, "064x")
    result = _rpc(
        "eth_call",
        [{"to": contract, "data": calldata}, "latest"],
    ).removeprefix("0x")

    if len(result) < 192:
        raise ChainError("Unexpected getBatch response from the contract")

    return {
        "root": "0x" + result[0:64].lower(),
        "leaf_count": int(result[64:128], 16),
        "anchored_at": int(result[128:192], 16),
    }


def anchor_root(root: str, leaf_count: int) -> AnchorReceipt:
    if not isinstance(root, str) or len(root) != 66 or not root.startswith("0x"):
        raise ValueError("root must be a 0x-prefixed 32-byte hex value")
    try:
        root_bytes = bytes.fromhex(root[2:])
    except ValueError as exc:
        raise ValueError("root must contain only hexadecimal characters") from exc
    if len(root_bytes) != 32:
        raise ValueError("root must be a 0x-prefixed 32-byte hex value")
    if not isinstance(leaf_count, int) or isinstance(leaf_count, bool):
        raise ValueError("leaf_count must be an integer")
    if not 1 <= leaf_count <= 0xFFFFFFFF:
        raise ValueError("leaf_count must be between 1 and 4294967295")
    if root_bytes == bytes(32):
        raise ValueError("root must not be empty")

    _, contract = _connection()
    normalized_root = "0x" + root_bytes.hex()
    calldata = (
        ANCHOR_ROOT_SELECTOR
        + root_bytes.hex()
        + format(leaf_count, "064x")
    )
    transaction_hash = _send_transaction(contract, calldata)
    chain_id = int(_rpc("eth_chainId", []), 16)
    return _wait_for_receipt(
        transaction_hash,
        normalized_root,
        leaf_count,
        chain_id,
    )
