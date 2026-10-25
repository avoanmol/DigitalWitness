"use client";
import { useState } from "react";
import type { Receipt } from "@/lib/types";
import { formatIST, formatSize, shortHash } from "@/lib/format";

export default function ReceiptCard({ receipt }: { receipt: Receipt }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(receipt.sha256);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  function download() {
    const blob = new Blob([JSON.stringify(receipt, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `receipt-${receipt.caseRef}-${shortHash(receipt.sha256)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const btn =
    "rounded-full border border-ink px-4 py-1.5 text-sm transition hover:bg-ink hover:text-paper";

  return (
    <div className="fade-up mx-auto mt-10 max-w-md rounded-3xl bg-card p-6">
      <div className="pop grid h-12 w-12 place-items-center rounded-full bg-accent text-white">
        ✓
      </div>
      <h2 className="mt-4 text-2xl font-semibold">Your evidence is saved</h2>
      <p className="text-sm text-muted">Case {receipt.caseRef}</p>

      <p className="mt-5 text-sm">
        {receipt.filename} · {formatSize(receipt.sizeBytes)}
      </p>
      <p className="text-sm text-muted" title={`${receipt.uploadedAt} (UTC)`}>
        Saved {formatIST(receipt.uploadedAt)}
      </p>

      <p className="mt-5 text-xs text-muted">Fingerprint (SHA-256)</p>
      <p className="break-all rounded-2xl bg-paper p-3 font-mono text-xs">{receipt.sha256}</p>

      <div className="mt-4 flex flex-wrap gap-2">
        <button onClick={copy} className={btn}>{copied ? "Copied" : "Copy fingerprint"}</button>
        <button onClick={download} className={btn}>Download receipt</button>
      </div>

      <p className="mt-6 text-xs text-muted">
        Keep this receipt. It shows this file was saved at the time above and has not changed
        since. It does not show that the content is true.
      </p>
    </div>
  );
}