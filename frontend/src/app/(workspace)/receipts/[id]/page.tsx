"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, getReceipt } from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/format";
import type { Receipt } from "@/lib/types";

export default function ReceiptPage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id);
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  useEffect(() => { getReceipt(id).then(setReceipt).catch((reason: unknown) => setError(reason instanceof ApiError ? reason.message : "Receipt could not be opened.")); }, [id]);

  function download() {
    if (!receipt) return;
    const blob = new Blob([JSON.stringify(receipt, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `${receipt.case_ref}-receipt.json`; anchor.click(); URL.revokeObjectURL(url);
  }
  async function copyHash() { if (!receipt) return; await navigator.clipboard.writeText(receipt.sha256); setCopied(true); window.setTimeout(() => setCopied(false), 1800); }

  return <div className="receipt-page">
    <div className="detail-back"><Link className="back-link" href="/cases">← Case workspace</Link></div>
    {error ? <div className="inline-error" role="alert"><strong>Receipt could not be loaded</strong><span>{error}</span><p>Receipts are kept for this browser session. If you opened this link in a new session, sign in and request the receipt from the API.</p></div> : !receipt ? <div className="table-state"><div className="spinner" /><span>Preparing your receipt…</span></div> : <>
      <div className="receipt-success-icon">✓</div><div className="eyebrow centered">SUBMISSION RECORDED</div><h1 className="receipt-title">Your receipt is ready.</h1><p className="receipt-subtitle">Keep this record with your case reference. It includes the fingerprint for the file you submitted.</p>
      <section className="panel receipt-card"><div className="receipt-card-top"><div><span className="eyebrow">DIGITALWITNESS RECEIPT</span><h2>{receipt.case_ref}</h2></div><span className="status-chip status-stored">{receipt.status}</span></div><div className="receipt-file"><span className="file-type-icon">▤</span><div><strong>{receipt.filename}</strong><span>{formatBytes(receipt.size_bytes)} <i>·</i> {formatDate(receipt.uploaded_at)}</span></div></div><div className="receipt-hash-block"><span>SHA-256 FILE FINGERPRINT</span><code>{receipt.sha256}</code><button className="button button-subtle" onClick={copyHash}>{copied ? "Copied" : "Copy hash"}</button></div><div className="receipt-detail-row"><span>Receipt ID</span><code>{receipt.receipt_id}</code></div><div className="receipt-detail-row"><span>Receipt signature</span><code className="receipt-signature">{receipt.signature || "Not returned by the API"}</code></div>{receipt.signature_valid !== undefined && <div className={`receipt-signature-check ${receipt.signature_valid ? "signature-valid" : "signature-invalid"}`} role="status">{receipt.signature_valid ? "Server signature verified" : "Server signature could not be verified"}</div>}<div className="receipt-warning"><span>i</span><p><strong>Keep this receipt safe.</strong> It records the file fingerprint and submission details. A matching hash means the file has not changed since the recorded point; it does not establish who created it or whether its contents are accurate.</p></div><div className="receipt-next-step"><strong>Next: review your case</strong><p>Open the case to check the saved evidence and any AI suggestions. When ready, choose <strong>Prepare complaint draft</strong> on the case page.</p></div><div className="receipt-actions"><Link href={`/cases/${receipt.case_id}`} className="button button-primary">Open case <span>→</span></Link><button className="button button-subtle" onClick={download}>Download receipt JSON <span>↓</span></button></div></section><Link className="text-link" href="/report/new">Submit another file <span>→</span></Link>
    </>}
  </div>;
}
