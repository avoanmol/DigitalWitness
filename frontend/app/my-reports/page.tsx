
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listCases, USE_MOCK } from "@/lib/api";
import { useUser } from "@/lib/auth";
import { emptyFilters } from "@/components/FilterBar";
import type { CaseSummary } from "@/lib/types";
import { formatIST } from "@/lib/format";
import { StatusPill } from "@/components/StatusPill";

const verificationLabels: Record<string, string> = {
  verified: "Verified",
  pending: "Pending anchor",
  altered: "Altered",
  error: "Could not verify",
};

export default function MyReportsPage() {
  const user = useUser();

  const [reports, setReports] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    if (!user && !USE_MOCK) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    listCases(emptyFilters, 1, 50)
      .then((result) => {
        if (!cancelled) setReports(result.items);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(
            e instanceof Error ? e.message : "Could not load reports."
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [user]);

  if (!user && !USE_MOCK) {
    return (
      <main className="mx-auto mt-20 max-w-sm px-5 text-center">
        <p className="text-xs uppercase tracking-[0.2em] text-muted">
          Reporter workspace
        </p>
        <h1 className="mt-3 text-2xl font-semibold">
          Please log in first
        </h1>
        <p className="mt-2 text-sm text-muted">
          Sign in to access your documented incidents.
        </p>
        <Link
          href="/login"
          className="mt-6 inline-block bg-ink px-6 py-3 text-sm text-paper"
        >
          Go to login
        </Link>
      </main>
    );
  }

  const evidenceTotal = reports.reduce(
    (sum, report) => sum + report.evidenceCount,
    0
  );

  const verifiedTotal = reports.filter(
    (report) => report.verification === "verified"
  ).length;

  const filteredReports = reports.filter((report) => {
    const matchesSearch =
      report.title.toLowerCase().includes(search.toLowerCase()) ||
      report.caseRef.toLowerCase().includes(search.toLowerCase());

    const matchesStatus =
      statusFilter === "all" ||
      report.status.toLowerCase() === statusFilter.toLowerCase();

    return matchesSearch && matchesStatus;
  });

  return (
    <main className="mx-auto mt-8 max-w-6xl px-4 pb-16 sm:px-6">
      {/* Page header */}
      <header className="flex flex-wrap items-end justify-between gap-5 border-b border-line pb-7">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted">
            Reporter workspace / Overview
          </p>

          <h1 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">
            My reports.
          </h1>

          <p className="mt-3 text-sm leading-6 text-muted">
            Your documented incidents and saved evidence, all in one place.
          </p>
        </div>

        <Link
          href="/report/new"
          className="bg-ink px-5 py-3 text-sm font-medium text-paper transition hover:opacity-85"
        >
          + New report
        </Link>
      </header>

      {/* Demo notice */}
      {USE_MOCK && (
        <div className="mt-6 border-l-2 border-muted pl-4">
          <p className="text-xs leading-5 text-muted">
            Demo mode: displayed records are synthetic examples,
            not real submissions.
          </p>
        </div>
      )}

      {/* Overview metrics */}
      <section className="mt-8 grid grid-cols-2 gap-x-6 sm:grid-cols-3">
        <div className="border-t border-line py-5">
          <p className="text-xs text-muted">Total reports</p>
          <p className="mt-3 text-3xl font-semibold tabular-nums">
            {loading ? "—" : reports.length}
          </p>
          <p className="mt-1 text-[11px] text-muted">
            Documented incidents
          </p>
        </div>

        <div className="border-t border-line py-5">
          <p className="text-xs text-muted">Evidence files</p>
          <p className="mt-3 text-3xl font-semibold tabular-nums">
            {loading ? "—" : evidenceTotal}
          </p>
          <p className="mt-1 text-[11px] text-muted">
            Files saved across reports
          </p>
        </div>

        <div className="col-span-2 border-t border-line py-5 sm:col-span-1">
          <p className="text-xs text-muted">Verified reports</p>
          <p className="mt-3 text-3xl font-semibold tabular-nums">
            {loading ? "—" : verifiedTotal}
          </p>
          <p className="mt-1 text-[11px] text-muted">
            Reports with verified evidence status
          </p>
        </div>
      </section>

      {/* Report list heading */}
      <section className="mt-8">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-line pb-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">
              Your records
            </p>
            <h2 className="mt-2 text-xl font-semibold">
              Recent activity
            </h2>
          </div>

          <span className="text-xs text-muted">
            {loading ? "Loading…" : `${filteredReports.length} records`}
          </span>
        </div>

        {/* Search and filters */}
        <div className="flex flex-col gap-3 border-b border-line py-4 sm:flex-row">
          <div className="relative flex-1">
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by title or case reference..."
              className="w-full border border-line bg-paper px-4 py-3 text-sm outline-none transition focus:border-ink"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-line bg-paper px-4 py-3 text-sm outline-none focus:border-ink sm:w-48"
          >
            <option value="all">All statuses</option>
            <option value="open">Open</option>
            <option value="under_review">Under review</option>
            <option value="closed">Closed</option>
          </select>
        </div>

        {/* Loading */}
        {loading ? (
          <div className="py-16 text-center">
            <p className="text-sm text-muted">
              Loading your reports…
            </p>
          </div>
        ) : error ? (
          <div className="border-b border-line py-12 text-center">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        ) : reports.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-xs uppercase tracking-[0.2em] text-muted">
              No records
            </p>
            <h3 className="mt-3 text-xl font-semibold">
              No reports yet.
            </h3>
            <p className="mt-2 text-sm text-muted">
              When you document an incident, it will appear here.
            </p>
            <Link
              href="/report/new"
              className="mt-6 inline-block border-b border-ink pb-1 text-sm font-medium"
            >
              Create your first report →
            </Link>
          </div>
        ) : filteredReports.length === 0 ? (
          <div className="py-14 text-center">
            <h3 className="text-base font-medium">
              No matching reports
            </h3>
            <p className="mt-2 text-sm text-muted">
              Try changing your search or status filter.
            </p>
            <button
              type="button"
              onClick={() => {
                setSearch("");
                setStatusFilter("all");
              }}
              className="mt-4 text-xs underline underline-offset-4"
            >
              Clear filters
            </button>
          </div>
        ) : (
          <div className="divide-y divide-line">
            {filteredReports.map((report, index) => (
              <article
                key={report.id}
                className="grid gap-4 py-6 sm:grid-cols-[1fr_auto] sm:items-center"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="text-[10px] font-medium uppercase tracking-wider text-muted">
                      {report.caseRef}
                    </span>
                    <span className="h-1 w-1 rounded-full bg-muted" />
                    <span className="text-[10px] text-muted">
                      {formatIST(report.createdAt)}
                    </span>
                  </div>

                  <h3 className="mt-3 break-words text-base font-semibold">
                    {report.title}
                  </h3>

                  <p className="mt-2 text-xs text-muted">
                    {report.evidenceCount} evidence file
                    {report.evidenceCount === 1 ? "" : "s"}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-x-5 gap-y-3 sm:justify-end">
                  <div className="flex items-center gap-2">
                    <StatusPill status={report.status} />
                  </div>

                  <div className="min-w-24">
                    <p className="text-[10px] uppercase tracking-wider text-muted">
                      Integrity
                    </p>
                    <p className="mt-1 text-xs font-medium">
                      {report.verification
                        ? verificationLabels[report.verification] ??
                          "Not checked"
                        : "Not checked"}
                    </p>
                  </div>

                  <Link
                    href={`/cases/${report.id}`}
                    className="border-b border-ink pb-1 text-xs font-semibold transition hover:opacity-60"
                  >
                    View report →
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {/* Integrity note */}
      <footer className="mt-9 border-t border-line pt-5">
        <p className="max-w-3xl text-xs leading-6 text-muted">
          An integrity status describes whether saved evidence matches
          its recorded fingerprint and proof. It does not establish
          whether the content of a file is true. A pending anchor is
          not, by itself, evidence of tampering.
        </p>
      </footer>
    </main>
  );
}
