"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getEvidence, getProof, verifyEvidence } from "@/lib/api";
import type { EvidenceItem, Proof, Verification } from "@/lib/types";
import EvidencePreview from "@/components/EvidencePreview";
import MetadataPanel from "@/components/MetadataPanel";
import VerifyBadge from "@/components/VerifyBadge";

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
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load the evidence"));
    getProof(id).then(setProof).catch(() => setProof(null));
  }, [id]);

  async function runVerify() {
    setChecking(true);
    setVerifyError("");
    try {
      setVerification(await verifyEvidence(id));
      getProof(id).then(setProof).catch(() => {});
    } catch (e) {
      setVerifyError(e instanceof Error ? e.message : "Verification failed");
    } finally {
      setChecking(false);
    }
  }

  if (error) return <p className="mt-10 text-center text-sm text-red-600">{error}</p>;
  if (!evidence) return <p className="mt-10 text-center text-sm text-muted">Loading evidence…</p>;

  const shown = verification?.result ?? evidence.verification ?? null;

  return (
    <main className="mt-6">
      <h1 className="fade-up break-all text-2xl font-semibold sm:text-3xl">{evidence.filename}</h1>

      <div className="fade-up mt-5 grid gap-4 lg:grid-cols-5" style={{ animationDelay: "80ms" }}>
        <section className="rounded-3xl bg-card p-4 lg:col-span-3">
          <EvidencePreview evidenceId={evidence.id} mimeType={evidence.mimeType} filename={evidence.filename} />
        </section>

        <div className="space-y-4 lg:col-span-2">
          <VerifyBadge
            result={shown}
            loading={checking}
            message={verification?.message}
            checkedAt={verification?.checkedAt}
          />

          <button
            onClick={runVerify}
            disabled={checking}
            className="group flex w-full items-center justify-between rounded-full bg-ink py-2 pl-6 pr-2 text-paper transition disabled:opacity-50"
          >
            <span>{checking ? "Checking…" : "Verify now"}</span>
            <span className="grid h-10 w-10 place-items-center rounded-full bg-paper text-ink transition group-hover:translate-x-0.5">
              →
            </span>
          </button>
          {verifyError && <p className="text-sm text-red-600">{verifyError}</p>}

          <MetadataPanel evidence={evidence} proof={proof} />

          {verification && (
            <details className="rounded-3xl bg-card p-5 text-sm">
              <summary className="cursor-pointer font-medium">Technical details</summary>
              <dl className="mt-3 space-y-2 break-all font-mono text-xs text-muted">
                <div><dt className="font-sans">Expected fingerprint</dt><dd>{verification.expectedHash}</dd></div>
                <div><dt className="font-sans">Fingerprint now</dt><dd>{verification.recomputedHash}</dd></div>
                {verification.onchainRoot && (
                  <div><dt className="font-sans">Root on blockchain</dt><dd>{verification.onchainRoot}</dd></div>
                )}
                {verification.computedRoot && (
                  <div><dt className="font-sans">Root we computed</dt><dd>{verification.computedRoot}</dd></div>
                )}
              </dl>
            </details>
          )}
        </div>
      </div>
    </main>
  );
}