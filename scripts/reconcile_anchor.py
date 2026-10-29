"""Attach a known transaction hash to a retained building batch and confirm it.

This command never sends an anchor transaction or releases evidence. Use only
when you have identified the transaction hash from the configured chain.
"""
import argparse
import re
from uuid import UUID
from backend.app.integrity.chain import get_chain_id, wait_for_anchor
from backend.app.integrity.persistence import confirm_submitted_batch, mark_batch_submitted
from backend.database import SessionLocal
from backend.models import MerkleBatch

parser=argparse.ArgumentParser()
parser.add_argument("batch_id", type=UUID, help="database Merkle batch UUID")
parser.add_argument("transaction_hash", help="already-broadcast 0x transaction hash")
args=parser.parse_args()
if not re.fullmatch(r"0x[0-9a-fA-F]{64}", args.transaction_hash):
    raise SystemExit("transaction_hash must be 0x-prefixed 32-byte hex")
with SessionLocal() as db:
    batch=db.get(MerkleBatch,args.batch_id)
    if batch is None: raise SystemExit("batch not found")
    if batch.status == "building":
        mark_batch_submitted(db,batch_id=batch.id,transaction_hash=args.transaction_hash,chain_id=get_chain_id())
        db.commit()
    elif batch.status != "submitted" or batch.tx_hash.lower() != args.transaction_hash.lower():
        raise SystemExit("batch is not building or already submitted with this transaction")
    root,count=batch.root_hash,batch.leaf_count
receipt=wait_for_anchor({"transaction_hash":args.transaction_hash.lower(),"chain_id":get_chain_id()},root,count)
with SessionLocal() as db:
    batch=confirm_submitted_batch(db,batch_id=args.batch_id,anchor_receipt=receipt)
    db.commit()
    print(f"Batch confirmed: {batch.id}; chain batch {batch.chain_batch_id}; tx {receipt['transaction_hash']}")
