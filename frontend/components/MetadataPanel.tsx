"use client";

import { useState, type ReactNode } from "react";
import type { EvidenceItem, Proof } from "@/lib/types";
import { formatIST, formatSize } from "@/lib/format";

function Row({
  label,
  title,
  children,
}: {
  label: string;
  title?: string;
  children: ReactNode;
}) {
  return (
    <div className="grid gap-1 border-b border-[#E5E2DA] py-3 last:border-b-0 sm:grid-cols-[145px_1fr] sm:gap-4">
      <dt className="text-xs text-[#77736B]">{label}</dt>
      <dd className="break-all text-sm text-[#242424]" title={title}>
        {children}
      </dd>
    </div>
  );
}

export default function MetadataPanel({
  evidence,
  proof,
}: {
  evidence: EvidenceItem;
  proof: Proof | null;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(evidence.sha256);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section className="border-t border-[#D8D5CD] pt-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold text-[#242424]">Details</h2>
        <span className="text-[10px] uppercase tracking-[0.16em] text-[#88847B]">
          File record
        </span>
      </div>

      <dl>
        <Row label="File">{evidence.filename}</Row>

        <Row label="Type and size">
          {evidence.mimeType} · {formatSize(evidence.sizeBytes)}
        </Row>

        <Row
          label="Uploaded"
          title={`${evidence.uploadedAt} (UTC)`}
        >
          {formatIST(evidence.uploadedAt)}
        </Row>

        <Row label="Status">
          {evidence.status} · analysis {evidence.analysisStatus}
        </Row>

        <Row label="Fingerprint (SHA-256)">
          <div className="flex flex-wrap items-start gap-2">
            <span className="min-w-0 flex-1 font-mono text-xs leading-5">
              {evidence.sha256}
            </span>

            <button
              type="button"
              onClick={copy}
              className="shrink-0 border border-[#BDB9AF] px-3 py-1 text-xs text-[#444] transition hover:border-[#242424] hover:bg-[#242424] hover:text-white"
            >
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </Row>

        {proof ? (
          <>
            <Row label="Batch">{proof.batchId}</Row>

            <Row label="Blockchain transaction">
              <a
                href={proof.explorerUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="break-all font-mono text-xs underline decoration-[#AD841E] underline-offset-4 hover:text-[#AD841E]"
              >
                {proof.txHash}
              </a>
            </Row>

            <Row label="Chain ID">{proof.chainId}</Row>
          </>
        ) : (
          <Row label="Anchor">Not anchored yet</Row>
        )}
      </dl>
    </section>
  );
}