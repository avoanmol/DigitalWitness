"use client";
import { useState, type ReactNode } from "react";
import type { EvidenceItem, Proof } from "@/lib/types";
import { formatIST, formatSize } from "@/lib/format";

function Row({ label, title, children }: { label: string; title?: string; children: ReactNode }) {
  return (
    <div className="py-2">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 break-all text-sm" title={title}>{children}</dd>
    </div>
  );
}

export default function MetadataPanel({ evidence, proof }: { evidence: EvidenceItem; proof: Proof | null }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(evidence.sha256);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <section className="rounded-3xl bg-card p-5">
      <h2 className="text-lg font-semibold">Details</h2>
      <dl className="mt-2 divide-y divide-line">
        <Row label="File">{evidence.filename}</Row>
        <Row label="Type and size">{evidence.mimeType} · {formatSize(evidence.sizeBytes)}</Row>
        <Row label="Uploaded" title={`${evidence.uploadedAt} (UTC)`}>{formatIST(evidence.uploadedAt)}</Row>
        <Row label="Status">{evidence.status} · analysis {evidence.analysisStatus}</Row>
        <Row label="Fingerprint (SHA-256)">
          <span className="font-mono text-xs">{evidence.sha256}</span>
          <button onClick={copy}
            className="ml-2 rounded-full border border-ink px-2.5 py-0.5 text-xs transition hover:bg-ink hover:text-paper">
            {copied ? "Copied" : "Copy"}
          </button>
        </Row>
        {proof ? (
          <>
            <Row label="Batch">{proof.batchId}</Row>
            <Row label="Blockchain transaction">
              <a href={proof.explorerUrl} target="_blank" rel="noopener noreferrer"
                className="font-mono text-xs underline hover:text-accent">
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