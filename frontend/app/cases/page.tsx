"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { listCases, USE_MOCK } from "@/lib/api";
import { useUser } from "@/lib/auth";
import type { CaseFilters, CaseSummary, Page } from "@/lib/types";
import FilterBar, { emptyFilters } from "@/components/FilterBar";
import CaseTable from "@/components/CaseTable";

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
    setLoading(true);
    listCases(filters, page)
      .then((d) => { if (!cancelled) { setData(d); setError(""); } })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Could not load cases");
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [filters, page, allowed]);

  function changeFilters(f: CaseFilters) {
    setFilters(f);
    setPage(1);
  }

  if (!allowed) {
    return (
      <main className="mx-auto mt-16 max-w-sm text-center">
        <h1 className="text-2xl font-semibold">
          {user ? "This area is for investigators" : "Please log in first"}
        </h1>
        <p className="mt-2 text-sm text-muted">
          {user ? "Your account can submit evidence but not review cases." : "Log in to review cases."}
        </p>
        <Link href={user ? "/report/new" : "/login"}
          className="mt-4 inline-block rounded-full bg-ink px-6 py-2 text-paper">
          {user ? "Go to reporting" : "Go to login"}
        </Link>
      </main>
    );
  }

  return (
    <main className="mt-8 space-y-4">
      <div className="fade-up">
        <h1 className="text-3xl font-semibold sm:text-4xl">Cases</h1>
        <p className="mt-1 text-sm text-muted">
          {data ? `${data.total} cases` : "Loading cases…"}
        </p>
      </div>
      <FilterBar filters={filters} onChange={changeFilters} />
      <CaseTable data={data} loading={loading} error={error} onPage={setPage} />
    </main>
  );
}