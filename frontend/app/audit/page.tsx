"use client";

import { useCallback, useEffect, useState } from "react";
import { useUser } from "@/lib/auth";
import { listAuditEvents, verifyAuditChain } from "@/lib/api";
import type { AuditEvent, AuditVerifyResult } from "@/lib/types";
import Link from "next/link";

const PAGE_SIZE = 20;

function formatDate(value: string) {
  return new Date(value).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function shortHash(value: string) {
  if (!value) return "—";
  return `${value.slice(0, 12)}...${value.slice(-8)}`;
}

function ActionBadge({ action }: { action: string }) {
  return (
    <span className="inline-flex rounded-full bg-card px-3 py-1 text-xs font-medium">
      {action.replaceAll("_", " ")}
    </span>
  );
}

export default function AuditPage() {
  const user = useUser();

  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [caseId, setCaseId] = useState("");
  const [evidenceId, setEvidenceId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const [verification, setVerification] =
    useState<AuditVerifyResult | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [verifyError, setVerifyError] = useState("");

  const allowed =
    !!user && ["legal", "admin", "investigator"].includes(user.role);

  const loadEvents = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await listAuditEvents(
        page,
        PAGE_SIZE,
        caseId.trim(),
        evidenceId.trim()
      );

      setEvents(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load audit events."
      );
    } finally {
      setLoading(false);
    }
  }, [page, caseId, evidenceId]);

  useEffect(() => {
    if (allowed) loadEvents();
  }, [allowed, loadEvents]);

  async function runVerification() {
    setVerifying(true);
    setVerifyError("");
    setVerification(null);

    try {
      const result = await verifyAuditChain();
      setVerification(result);
    } catch (err) {
      setVerifyError(
        err instanceof Error ? err.message : "Verification failed."
      );
    } finally {
      setVerifying(false);
    }
  }

  function applyFilters() {
    setPage(1);
    setExpanded(null);
  }

  if (!user) {
    return (
      <main className="mx-auto mt-16 max-w-md text-center">
        <h1 className="text-2xl font-semibold">Login required</h1>
        <p className="mt-2 text-sm text-muted">
          Log in to access the audit trail.
        </p>
        <Link
          href="/login"
          className="mt-5 inline-block rounded-full bg-ink px-6 py-3 text-paper"
        >
          Go to login
        </Link>
      </main>
    );
  }

  if (!allowed) {
    return (
      <main className="mx-auto mt-16 max-w-md text-center">
        <h1 className="text-2xl font-semibold">Access restricted</h1>
        <p className="mt-2 text-sm text-muted">
          Your account does not have permission to view the audit trail.
        </p>
        <Link
          href="/cases"
          className="mt-5 inline-block rounded-full bg-ink px-6 py-3 text-paper"
        >
          Back to cases
        </Link>
      </main>
    );
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <main className="mt-8 space-y-6">
      {/* Header */}
      <section className="fade-up flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
            Security and accountability
          </p>
          <h1 className="mt-2 text-3xl font-semibold sm:text-4xl">
            Audit Trail
          </h1>
          <p className="mt-2 max-w-xl text-sm text-muted">
            A chronological record of system activity, evidence access and
            case operations.
          </p>
        </div>

        <button
          onClick={loadEvents}
          disabled={loading}
          className="rounded-full border border-line px-5 py-2.5 text-sm transition hover:bg-card disabled:opacity-50"
        >
          {loading ? "Refreshing..." : "Refresh logs"}
        </button>
      </section>

      {/* Verification card */}
      <section className="rounded-3xl bg-ink p-5 text-paper sm:p-7">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-white/50">
              Integrity check
            </p>
            <h2 className="mt-2 text-xl font-semibold">
              Audit hash-chain verification
            </h2>
            <p className="mt-2 max-w-lg text-sm text-white/60">
              Check whether the recorded audit events maintain their
              cryptographic hash-chain integrity.
            </p>
          </div>

          <button
            onClick={runVerification}
            disabled={verifying}
            className="shrink-0 rounded-full bg-paper px-6 py-3 text-sm font-semibold text-ink transition hover:opacity-90 disabled:opacity-50"
          >
            {verifying ? "Verifying..." : "Verify chain"}
          </button>
        </div>

        {verification && (
          <div
            className={`mt-5 rounded-2xl p-4 ${
              verification.valid
                ? "bg-emerald-400/15 text-emerald-200"
                : "bg-red-400/15 text-red-200"
            }`}
            role="status"
          >
            <p className="font-semibold">
              {verification.valid
                ? "✓ Audit chain integrity verified"
                : "⚠ Audit chain integrity check failed"}
            </p>

            {!verification.valid && (
              <p className="mt-1 text-sm">
                Broken sequence: {verification.brokenAtSeq ?? "Not specified"}
              </p>
            )}
          </div>
        )}

        {verifyError && (
          <p className="mt-4 text-sm text-red-200" role="alert">
            {verifyError}
          </p>
        )}
      </section>

      {/* Filters */}
      <section className="rounded-3xl bg-card p-5">
        <div className="mb-4">
          <h2 className="font-semibold">Filter audit events</h2>
          <p className="mt-1 text-xs text-muted">
            Search by case ID or evidence ID.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <input
            value={caseId}
            onChange={(e) => setCaseId(e.target.value)}
            placeholder="Enter case ID"
            className="w-full rounded-xl border border-line bg-paper p-3 text-sm outline-none focus:border-ink"
          />

          <input
            value={evidenceId}
            onChange={(e) => setEvidenceId(e.target.value)}
            placeholder="Enter evidence ID"
            className="w-full rounded-xl border border-line bg-paper p-3 text-sm outline-none focus:border-ink"
          />
        </div>

        <button
          onClick={applyFilters}
          className="mt-3 rounded-full bg-ink px-5 py-2.5 text-sm text-paper"
        >
          Apply filters
        </button>
      </section>

      {/* Events */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">Activity history</h2>
            <p className="mt-1 text-sm text-muted">
              {total} recorded event{total === 1 ? "" : "s"}
            </p>
          </div>

          <span className="rounded-full bg-card px-3 py-1.5 text-xs text-muted">
            Page {page} of {totalPages}
          </span>
        </div>

        {loading && (
          <div className="space-y-3" aria-busy="true">
            {[1, 2, 3].map((item) => (
              <div
                key={item}
                className="h-24 animate-pulse rounded-2xl bg-card"
              />
            ))}
          </div>
        )}

        {!loading && error && (
          <div className="rounded-3xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
            <p className="font-semibold">Could not load audit events</p>
            <p className="mt-1">{error}</p>
            <button
              onClick={loadEvents}
              className="mt-3 underline"
            >
              Try again
            </button>
          </div>
        )}

        {!loading && !error && events.length === 0 && (
          <div className="rounded-3xl bg-card p-10 text-center">
            <h3 className="font-semibold">No audit events found</h3>
            <p className="mt-2 text-sm text-muted">
              Events will appear here when recorded by the backend.
            </p>
          </div>
        )}

        {!loading && !error && events.length > 0 && (
          <div className="space-y-3">
            {events.map((event) => (
              <article
                key={event.id}
                className="overflow-hidden rounded-2xl border border-line bg-paper"
              >
                <button
                  onClick={() =>
                    setExpanded(
                      expanded === event.id ? null : event.id
                    )
                  }
                  className="flex w-full flex-col gap-3 p-4 text-left transition hover:bg-card sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-semibold text-muted">
                        #{event.seq}
                      </span>
                      <ActionBadge action={event.action} />
                    </div>

                    <p className="mt-2 break-all text-sm font-medium">
                      {event.targetType}
                      {event.targetId ? ` · ${event.targetId}` : ""}
                    </p>

                    <p className="mt-1 text-xs text-muted">
                      {event.actorRole} · {event.actorId ?? "Unknown actor"}
                    </p>
                  </div>

                  <div className="flex shrink-0 items-center justify-between gap-4 sm:flex-col sm:items-end">
                    <span className="text-xs text-muted">
                      {formatDate(event.createdAt)}
                    </span>
                    <span className="text-xs text-muted">
                      {expanded === event.id ? "Hide details −" : "Details +"}
                    </span>
                  </div>
                </button>

                {expanded === event.id && (
                  <div className="space-y-4 border-t border-line bg-card p-4">
                    <div className="grid gap-3 text-sm sm:grid-cols-2">
                      <div>
                        <p className="text-xs text-muted">Case ID</p>
                        <p className="mt-1 break-all">
                          {event.caseId ?? "—"}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs text-muted">IP address</p>
                        <p className="mt-1">{event.ip ?? "—"}</p>
                      </div>

                      <div>
                        <p className="text-xs text-muted">Previous hash</p>
                        <p className="mt-1 break-all font-mono text-xs">
                          {shortHash(event.prevHash)}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs text-muted">Entry hash</p>
                        <p className="mt-1 break-all font-mono text-xs">
                          {shortHash(event.entryHash)}
                        </p>
                      </div>
                    </div>

                    <div>
                      <p className="mb-2 text-xs font-semibold text-muted">
                        EVENT DETAILS
                      </p>
                      <pre className="overflow-x-auto rounded-xl bg-paper p-4 text-xs leading-relaxed">
                        {JSON.stringify(event.details, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </article>
            ))}
          </div>
        )}

        {/* Pagination */}
        {!loading && !error && total > PAGE_SIZE && (
          <div className="mt-5 flex items-center justify-between">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="rounded-full border border-line px-5 py-2 text-sm disabled:opacity-30"
            >
              Previous
            </button>

            <span className="text-xs text-muted">
              {page} / {totalPages}
            </span>

            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="rounded-full border border-line px-5 py-2 text-sm disabled:opacity-30"
            >
              Next
            </button>
          </div>
        )}
      </section>
    </main>
  );
}