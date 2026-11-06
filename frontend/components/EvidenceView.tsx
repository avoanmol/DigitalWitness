"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getEvidence, getProof, verifyEvidence } from "@/lib/api";
import type { EvidenceItem, Proof, Verification } from "@/lib/types";
import EvidencePreview from "@/components/EvidencePreview";
import MetadataPanel from "@/components/MetadataPanel";
import VerifyBadge from "@/components/VerifyBadge";
import AnalysisPanel from "@/components/AnalysisPanel";

export default function EvidenceView() {
  const { id } = useParams<{ id: string }>();

  const [evidence, setEvidence] = useState<EvidenceItem | null>(null);
  const [proof, setProof] = useState<Proof | null>(null);
  const [verification, setVerification] = useState<Verification | null>(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");
  const [verifyError, setVerifyError] = useState("");

  useEffect(() => {
    getEvidence(id)
      .then(setEvidence)
      .catch((e) =>
        setError(
          e instanceof Error ? e.message : "Could not load the evidence"
        )
      );

    getProof(id).then(setProof).catch(() => setProof(null));
  }, [id]);

  async function runVerify() {
    setChecking(true);
    setVerifyError("");

    try {
      setVerification(await verifyEvidence(id));
      getProof(id).then(setProof).catch(() => {});
    } catch (e) {
      setVerifyError(
        e instanceof Error ? e.message : "Verification failed"
      );
    } finally {
      setChecking(false);
    }
  }

  if (error) {
    return (
      <p className="mt-10 text-center text-sm text-red-600">{error}</p>
    );
  }

  if (!evidence) {
    return (
      <p className="mt-10 text-center text-sm text-muted">
        Loading evidence...
      </p>
    );
  }

  const shown = verification?.result ?? evidence.verification ?? null;

  return (
    <main className="mx-auto mt-10 max-w-7xl px-5 pb-16 sm:px-10">

      {/* PAGE HEADING */}
      <div className="mb-10 border-b border-[#e5e5e5] pb-7">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#AD841E]">
          Evidence record
        </p>

        <h1 className="mt-3 break-all text-2xl font-semibold tracking-tight sm:text-3xl">
          {evidence.filename}
        </h1>

        <p className="mt-2 text-sm text-[#777]">
          Review the original file, its integrity status and associated records.
        </p>
      </div>

      {/* MAIN CONTENT */}
      <div className="grid gap-12 lg:grid-cols-5">

        {/* FILE PREVIEW */}
        <section className="lg:col-span-3">
          <div className="mb-4 flex items-center justify-between border-b border-[#e5e5e5] pb-3">
            <h2 className="text-sm font-semibold">Original evidence</h2>
            <span className="text-xs text-[#888]">File preview</span>
          </div>

          <EvidencePreview
            evidenceId={evidence.id}
            mimeType={evidence.mimeType}
            filename={evidence.filename}
          />
        </section>

        {/* VERIFICATION AND DETAILS */}
        <div className="space-y-8 lg:col-span-2">

          <section>
            <div className="mb-4 border-b border-[#e5e5e5] pb-3">
              <h2 className="text-sm font-semibold">
                Integrity verification
              </h2>
            </div>

            <VerifyBadge
              result={shown}
              loading={checking}
              message={verification?.message}
              checkedAt={verification?.checkedAt}
            />

            <button
              onClick={runVerify}
              disabled={checking}
              className="mt-5 flex w-full items-center justify-between border border-[#242424] bg-[#242424] px-5 py-4 text-sm font-medium text-white transition hover:bg-white hover:text-[#242424] disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span>{checking ? "Checking..." : "Verify evidence"}</span>
              <span aria-hidden="true">→</span>
            </button>

            {verifyError && (
              <p className="mt-3 text-sm text-red-600">{verifyError}</p>
            )}
          </section>

          <section>
            <div className="mb-4 border-b border-[#e5e5e5] pb-3">
              <h2 className="text-sm font-semibold">Evidence details</h2>
            </div>

            <MetadataPanel evidence={evidence} proof={proof} />
          </section>

          {/* TECHNICAL DETAILS */}
          {verification && (
            <details className="border-y border-[#e5e5e5] py-4 text-sm">
              <summary className="cursor-pointer font-medium">
                Technical verification details
              </summary>

              <dl className="mt-5 space-y-4 break-all font-mono text-xs text-[#666]">
                <div>
                  <dt className="font-sans font-semibold text-[#242424]">
                    Expected fingerprint
                  </dt>
                  <dd className="mt-1">{verification.expectedHash}</dd>
                </div>

                <div>
                  <dt className="font-sans font-semibold text-[#242424]">
                    Fingerprint now
                  </dt>
                  <dd className="mt-1">{verification.recomputedHash}</dd>
                </div>

                {verification.onchainRoot && (
                  <div>
                    <dt className="font-sans font-semibold text-[#242424]">
                      Root on blockchain
                    </dt>
                    <dd className="mt-1">{verification.onchainRoot}</dd>
                  </div>
                )}

                {verification.computedRoot && (
                  <div>
                    <dt className="font-sans font-semibold text-[#242424]">
                      Root we computed
                    </dt>
                    <dd className="mt-1">{verification.computedRoot}</dd>
                  </div>
                )}
              </dl>
            </details>
          )}
        </div>
      </div>

      {/* AI ANALYSIS */}
      <section className="mt-16 border-t border-[#e5e5e5] pt-10">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-[#AD841E]">
          Investigative assistance
        </p>

        <h2 className="mb-7 text-2xl font-semibold tracking-tight">
          AI-assisted analysis
        </h2>

        <AnalysisPanel evidenceId={evidence.id} />
      </section>

    </main>
  );
}