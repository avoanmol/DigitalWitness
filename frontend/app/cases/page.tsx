
"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { listCases, USE_MOCK } from "@/lib/api";
import { useUser } from "@/lib/auth";
import type { CaseFilters, CaseSummary, Page } from "@/lib/types";
import FilterBar, { emptyFilters } from "@/components/FilterBar";
import CaseTable from "@/components/CaseTable";

function SummaryCard({
  label,
  value,
  note,
}: {
  label: string;
  value: number | string;
  note: string;
}) {
  return (
    <section className="border border-line bg-paper p-5">
      <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">
        {label}
      </p>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-ink">
        {value}
      </p>
      <p className="mt-2 text-xs text-muted">{note}</p>
    </section>
  );
}

export default function CasesPage() {
  const user = useUser();

  const [filters, setFilters] = useState<CaseFilters>(emptyFilters);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<CaseSummary> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const allowed = USE_MOCK || (!!user && user.role !== "reporter");

  useEffect(() => {
    if (!allowed) return;

    let cancelled = false;

    listCases(filters, page)
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setError("");
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(
            e instanceof Error ? e.message : "Could not load cases"
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [filters, page, allowed]);

  function changeFilters(nextFilters: CaseFilters) {
    setLoading(true);
    setFilters(nextFilters);
    setPage(1);
  }

  const visibleCases = data?.items ?? [];

  const summary = useMemo(() => {
    return {
      underReview: visibleCases.filter(
        (item) => item.status === "under_review"
      ).length,

      highPriority: visibleCases.filter(
        (item) =>
          item.topSeverity === "high" ||
          item.topSeverity === "critical"
      ).length,

      pendingVerification: visibleCases.filter(
        (item) =>
          !item.verification ||
          item.verification === "pending" ||
          item.verification === "error"
      ).length,
    };
  }, [visibleCases]);

  if (!allowed) {
    return (
      <main className="mx-auto mt-16 max-w-md text-center">
        <h1 className="text-2xl font-semibold text-ink">
          {user
            ? "This area is for investigators"
            : "Please log in first"}
        </h1>

        <p className="mt-3 text-sm leading-6 text-muted">
          {user
            ? "Your account can submit evidence but cannot review cases."
            : "Log in with an authorised account to access the investigation desk."}
        </p>

        <Link
          href={user ? "/report/new" : "/login"}
          className="mt-6 inline-block border border-ink bg-ink px-5 py-3 text-sm text-paper transition hover:bg-transparent hover:text-ink"
        >
          {user ? "Go to reporting" : "Log in"}
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto mt-8 max-w-7xl space-y-8 pb-12">
      {/* Page heading */}
      <header className="flex flex-col justify-between gap-4 border-b border-line pb-6 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted">
            DigitalWitness / Workspace
          </p>

          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            Investigation desk
          </h1>

          <p className="mt-2 max-w-xl text-sm leading-6 text-muted">
            Review submitted cases, inspect evidence integrity and follow up
            on items requiring human attention.
          </p>
        </div>

        <div className="text-sm text-muted">
          <span className="font-medium text-ink">
            {user?.fullName ?? "Reviewer"}
          </span>
          <span className="mx-2">/</span>
          <span className="capitalize">{user?.role ?? "reviewer"}</span>
        </div>
      </header>

      {/* Overview */}
      <section>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-ink">
              Case overview
            </h2>
            <p className="mt-1 text-xs text-muted">
              Summary of the currently loaded results.
            </p>
          </div>

          <p className="text-xs text-muted">
            {loading
              ? "Updating results…"
              : `${data?.total ?? 0} matching cases`}
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryCard
            label="Total cases"
            value={data?.total ?? "—"}
            note="Cases matching the current filters"
          />

          <SummaryCard
            label="Under review"
            value={loading ? "—" : summary.underReview}
            note="In the currently loaded page"
          />

          <SummaryCard
            label="High priority"
            value={loading ? "—" : summary.highPriority}
            note="High or critical severity on this page"
          />

          <SummaryCard
            label="Verification follow-up"
            value={loading ? "—" : summary.pendingVerification}
            note="Pending, unavailable or errored checks on this page"
          />
        </div>
      </section>

      {/* Review queue */}
      <section>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-ink">
              Case register
            </h2>
            <p className="mt-1 text-xs text-muted">
              Search and filter submissions before opening a case.
            </p>
          </div>

          {data && (
            <p className="text-xs text-muted">
              Page {data.page} · {data.items.length} records shown
            </p>
          )}
        </div>

        <FilterBar
          filters={filters}
          onChange={changeFilters}
        />

        <div className="mt-5">
          <CaseTable
            data={data}
            loading={loading}
            error={error}
            onPage={(nextPage) => {
              setLoading(true);
              setPage(nextPage);
            }}
          />
        </div>
      </section>

      {/* Guidance */}
      <section className="border-t border-line pt-5">
        <p className="text-xs leading-6 text-muted">
          Review original evidence and its surrounding context before
          recording a decision. AI observations are review leads, not
          conclusions. An integrity check indicates whether stored evidence
          matches its recorded fingerprint; it does not establish whether
          the content itself is true.
        </p>
      </section>
    </main>
  );
}
