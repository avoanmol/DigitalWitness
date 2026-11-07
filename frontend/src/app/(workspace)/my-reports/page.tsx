"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, getCases, isMockMode } from "@/lib/api";
import { formatDate, titleCase } from "@/lib/format";
import type { CaseSummary } from "@/lib/types";
import { VerifyBadge } from "@/components/verify-badge";
import { useSessionUser } from "@/lib/session";

export default function MyReportsPage() {
  const user = useSessionUser();
  const [reports, setReports] = useState<CaseSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    if (user?.role !== "reporter") return;
    let active = true;
    getCases({ q: search.trim() || undefined, status: status as CaseSummary["status"] | "", page: 1, page_size: 100 })
      .then((result) => { if (active) { setReports(result.items); setTotal(result.total); setError(""); } })
      .catch((reason: unknown) => { if (active) setError(reason instanceof ApiError ? reason.message : "Could not load your reports."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [user, search, status, refresh]);

  if (user?.role !== "reporter") return <div className="inline-error" role="alert"><strong>Reporter workspace only</strong><span>Your reports are available to reporter accounts.</span><Link className="button button-subtle" href="/cases">Open case workspace</Link></div>;

  const evidenceTotal = reports.reduce((sum, report) => sum + report.evidence_count, 0);
  const verifiedTotal = reports.filter((report) => report.verification === "verified").length;

  return <main className="pr-reports-page">
    <header className="pr-page-header"><div><p className="pr-eyebrow">REPORTER WORKSPACE / OVERVIEW</p><h1>My reports.</h1><p>Your documented incidents and saved evidence, in one place.</p></div><Link className="button button-primary" href="/report/new"><span aria-hidden="true">＋</span> New report</Link></header>
    {isMockMode() && <p className="pr-demo-note">Demo mode: displayed records are synthetic examples, not real submissions.</p>}
    <section className="pr-report-metrics" aria-label="Report summary">
      <article><span>Reports shown</span><strong>{loading ? "—" : total}</strong><small>Documented incidents</small></article>
      <article><span>Evidence files</span><strong>{loading ? "—" : evidenceTotal}</strong><small>Across the loaded reports</small></article>
      <article><span>Verified reports</span><strong>{loading ? "—" : verifiedTotal}</strong><small>Among the loaded results</small></article>
    </section>
    <section className="pr-report-list">
      <div className="pr-report-list-head"><div><p className="pr-eyebrow">YOUR RECORDS</p><h2>Recent activity</h2></div><span>{loading ? "Loading…" : `${reports.length} records shown`}</span></div>
      <form className="pr-report-filters" onSubmit={(event) => event.preventDefault()}>
        <label><span className="sr-only">Search reports</span><input type="search" value={search} onChange={(event) => { setSearch(event.target.value); setLoading(true); }} placeholder="Search by title or case reference" /></label>
        <label><span className="sr-only">Filter by case status</span><select value={status} onChange={(event) => { setStatus(event.target.value); setLoading(true); }}><option value="">All statuses</option><option value="open">Open</option><option value="under_review">Under review</option><option value="closed">Closed</option></select></label>
      </form>
      {loading ? <div className="pr-reports-state" aria-live="polite">Loading your reports…</div> : error ? <div className="inline-error" role="alert"><strong>Reports could not be loaded</strong><span>{error}</span><button className="button button-subtle" onClick={() => setRefresh((value) => value + 1)}>Try again</button></div> : reports.length === 0 ? <div className="pr-reports-state"><p className="pr-eyebrow">NO RECORDS</p><h3>{search || status ? "No matching reports." : "No reports yet."}</h3><p>{search || status ? "Try changing your search or status filter." : "When you document an incident, it will appear here."}</p>{search || status ? <button className="button button-subtle" onClick={() => { setSearch(""); setStatus(""); }}>Clear filters</button> : <Link className="text-link" href="/report/new">Create your first report <span aria-hidden="true">→</span></Link>}</div> : <div className="pr-report-rows">{reports.map((report) => <article className="pr-report-row" key={report.id}>
        <div className="pr-report-main"><div className="pr-report-meta"><span>{report.case_ref}</span><span aria-hidden="true">·</span><time dateTime={report.created_at}>{formatDate(report.created_at)}</time></div><h3>{report.title}</h3><p>{report.evidence_count} evidence file{report.evidence_count === 1 ? "" : "s"}</p></div>
        <div className="pr-report-side"><span className={`status-chip status-${report.status}`}>{titleCase(report.status)}</span><div><small>INTEGRITY</small><VerifyBadge compact result={report.verification} /></div><Link className="pr-report-link" href={`/cases/${report.id}`}>View report <span aria-hidden="true">→</span></Link></div>
      </article>)}</div>}
    </section>
    <footer className="pr-report-note">An integrity status describes whether saved evidence matches its recorded fingerprint and proof. It does not establish whether the content is true. A pending anchor is not, by itself, evidence of tampering.</footer>
  </main>;
}
