
"use client";

import { useState } from "react";
import type { Receipt } from "@/lib/types";
import { formatIST, formatSize, shortHash } from "@/lib/format";

export default function ReceiptCard({ receipt }: { receipt: Receipt }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(receipt.sha256);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  function download() {
    const blob = new Blob(
      [JSON.stringify(receipt, null, 2)],
      { type: "application/json" },
    );

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");

    a.href = url;
    a.download = `receipt-${receipt.caseRef}-${shortHash(receipt.sha256)}.json`;
    a.click();

    URL.revokeObjectURL(url);
  }

  const buttonStyle =
    "inline-flex items-center justify-center border border-[#242424] px-5 py-3 text-sm font-medium transition hover:bg-[#242424] hover:text-white";

  return (
    <main className="fade-up mx-auto mt-10 w-full max-w-3xl">
      <div className="border-b border-[#E5E3DD] pb-8">
        <div className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center border border-emerald-600 text-lg text-emerald-700">
            ✓
          </span>

          <span className="text-xs font-semibold uppercase tracking-[0.15em] text-emerald-700">
            Upload successful
          </span>
        </div>

        <h1 className="mt-6">Your evidence is saved</h1>

        <p className="mt-4 text-sm leading-8 text-[#777777]">
          Your file has been saved and a SHA-256 fingerprint has been
          generated for its integrity record.
        </p>

        <p className="mt-5 text-sm font-medium text-[#242424]">
          Case reference: {receipt.caseRef}
        </p>
      </div>

      <section className="py-8">
        <h2 className="text-base">File details</h2>

        <dl className="mt-5 divide-y divide-[#E5E3DD] border-y border-[#E5E3DD]">
          <div className="grid gap-2 py-4 sm:grid-cols-[150px_1fr] sm:gap-6">
            <dt className="text-sm text-[#777777]">File name</dt>
            <dd className="break-all text-sm font-medium">{receipt.filename}</dd>
          </div>

          <div className="grid gap-2 py-4 sm:grid-cols-[150px_1fr] sm:gap-6">
            <dt className="text-sm text-[#777777]">File size</dt>
            <dd className="text-sm">{formatSize(receipt.sizeBytes)}</dd>
          </div>

          <div className="grid gap-2 py-4 sm:grid-cols-[150px_1fr] sm:gap-6">
            <dt className="text-sm text-[#777777]">Saved on</dt>
            <dd
              className="text-sm"
              title={`${receipt.uploadedAt} (UTC)`}
            >
              {formatIST(receipt.uploadedAt)}
            </dd>
          </div>
        </dl>
      </section>

      <section className="border-t border-[#E5E3DD] py-8">
        <h2 className="text-base">Evidence fingerprint</h2>

        <p className="mt-3 text-sm leading-7 text-[#777777]">
          This SHA-256 fingerprint uniquely represents the uploaded file.
          Keep it with your receipt for future integrity checks.
        </p>

        <div className="mt-5 border border-[#E5E3DD] bg-[#F8F7F4] p-5">
          <p className="break-all font-mono text-xs leading-7 text-[#242424]">
            {receipt.sha256}
          </p>
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <button type="button" onClick={copy} className={buttonStyle}>
            {copied ? "Copied" : "Copy fingerprint"}
          </button>

          <button type="button" onClick={download} className={buttonStyle}>
            Download receipt
          </button>
        </div>
      </section>

      <footer className="border-t border-[#E5E3DD] py-7">
        <p className="text-sm leading-8 text-[#777777]">
          Keep this receipt. It records that the file was saved at the
          time shown above. Its fingerprint can help establish whether
          the file has changed since it was recorded. It does not prove
          that the content itself is true.
        </p>
      </footer>
    </main>
  );
}
