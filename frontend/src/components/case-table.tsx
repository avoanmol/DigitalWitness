"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ApiError, getCases } from "@/lib/api";
import { formatDate, titleCase } from "@/lib/format";
import type { CaseSummary, VerificationResult } from "@/lib/types";
import { VerifyBadge } from "@/components/verify-badge";
import { useSessionUser } from "@/lib/session";

export function CaseTable() {
  const user = useSessionUser();
  const isInvestigator = user?.role === "investigator";
  const isReporter = user?.role === "reporter";
  const canSubmit = isReporter;
  const [items, setItems] = useState<CaseSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [verification, setVerification] = useState("");
  const [severity, setSeverity] = useState("");
  const [threatClass, setThreatClass] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [loadedQuery, setLoadedQuery] = useState("");
  const [loadError, setLoadError] = useState("");
  const [errorQuery, setErrorQuery] = useState("");
  const [refresh, setRefresh] = useState(0);
  const pageSize = 8;
  const queryKey = JSON.stringify([q, status, verification, severity, threatClass, from, to, page, refresh]);
  const loading = loadedQuery !== queryKey;
  const error = errorQuery === queryKey ? loadError : "";

  useEffect(() => {
    let alive = true;
    getCases({ q, status: status as CaseSummary["status"] | "", verification: verification as VerificationResult | "", severity, threat_class: threatClass, from, to, page, page_size: pageSize })
      .then((result) => { if (alive) { setItems(result.items); setTotal(result.total); setLoadError(""); setErrorQuery(""); setLoadedQuery(queryKey); } })
      .catch((reason: unknown) => { if (alive) { setLoadError(reason instanceof ApiError ? reason.message : "Could not load cases."); setErrorQuery(queryKey); setLoadedQuery(queryKey); } });
    return () => { alive = false; };
  }, [q, status, verification, severity, threatClass, from, to, page, refresh, queryKey]);

  const maxPage = Math.max(1, Math.ceil(total / pageSize));
  const stats = useMemo(() => ({ total, needsReview: items.filter((item) => item.pending_count > 0).length, verified: items.filter((item) => item.verification === "verified").length }), [items, total]);

  return <>
    <div className="page-heading heading-row"><div><div className="eyebrow">{isInvestigator ? "INVESTIGATION" : isReporter ? "YOUR DOCUMENTATION" : "CASEWORK"}</div><h1>{isInvestigator ? "Investigation desk" : isReporter ? "My reports" : "Case workspace"}</h1><p>{isInvestigator ? "Review reporter-submitted cases, inspect original evidence and record your decisions." : isReporter ? "Continue documenting an incident or review evidence you have already submitted." : "Review case status, evidence integrity and recorded investigation decisions."}</p></div>{canSubmit && <Link className="button button-primary" href="/report/new"><span>＋</span> New report</Link>}</div>
    <section className="stat-grid" aria-label="Case summary">
      <div className="stat-card"><span className="stat-label">Cases in view</span><strong>{stats.total}</strong><span className="stat-foot">Across your workspace</span><span className="stat-symbol">▦</span></div>
      <div className="stat-card"><span className="stat-label">Evidence awaiting anchor</span><strong>{items.reduce((sum, item) => sum + item.pending_count, 0)}</strong><span className="stat-foot">Not yet included in a confirmed batch</span><span className="stat-symbol amber">◷</span></div>
      <div className="stat-card"><span className="stat-label">Verified cases</span><strong>{stats.verified}</strong><span className="stat-foot">Unchanged since anchoring</span><span className="stat-symbol green">✓</span></div>
      <div className="stat-card"><span className="stat-label">AI suggestions</span><strong>{items.reduce((sum, item) => sum + item.threat_count, 0)}</strong><span className="stat-foot">Human review required</span><span className="stat-symbol violet">✳</span></div>
    </section>
    <section className="panel case-panel">
      <div className="panel-title-row"><div><h2>{isInvestigator ? "Reporter submissions" : isReporter ? "Your reports" : "All cases"}</h2><p>{isInvestigator ? "Open a report to review the timeline, original files, AI leads and possible connections." : "Use filters to narrow the case list."}</p></div><span className="count-pill">{total} records</span></div>
      <div className="filter-grid">
        <label className="search-control"><span aria-hidden="true">⌕</span><input aria-label="Search cases" placeholder="Search case ID or title" value={q} onChange={(event) => { setQ(event.target.value); setPage(1); }} /></label>
        <label><span className="sr-only">Status</span><select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="">Any status</option><option value="open">Open</option><option value="under_review">Under review</option><option value="closed">Closed</option></select></label>
        <label><span className="sr-only">Verification</span><select value={verification} onChange={(event) => { setVerification(event.target.value); setPage(1); }}><option value="">Any verification</option><option value="verified">Verified</option><option value="altered">Altered</option><option value="pending">Pending anchor</option><option value="not_checked">Not checked</option><option value="error">Check unavailable</option></select></label>
        <label><span className="sr-only">Severity</span><select value={severity} onChange={(event) => { setSeverity(event.target.value); setPage(1); }}><option value="">Any severity</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label>
        <label><span className="sr-only">Threat class</span><input placeholder="Threat class" value={threatClass} onChange={(event) => { setThreatClass(event.target.value); setPage(1); }} /></label>
        <label><span className="sr-only">From date</span><input type="date" aria-label="From date" value={from} onChange={(event) => { setFrom(event.target.value); setPage(1); }} /></label>
        <label><span className="sr-only">To date</span><input type="date" aria-label="To date" value={to} onChange={(event) => { setTo(event.target.value); setPage(1); }} /></label>
        <button className="button button-subtle filter-clear" onClick={() => { setQ(""); setStatus(""); setVerification(""); setSeverity(""); setThreatClass(""); setFrom(""); setTo(""); setPage(1); }}>Clear filters</button>
      </div>
      {loading ? <div className="table-state"><div className="spinner" /><span>Loading cases…</span></div> : error ? <div className="inline-error" role="alert"><strong>Cases could not be loaded</strong><span>{error}</span><button className="button button-subtle" onClick={() => setRefresh((value) => value + 1)}>Try again</button></div> : items.length === 0 ? <div className="empty-state"><div className="empty-icon">⌕</div><h3>{isInvestigator ? "No reporter submissions to review" : "No cases match these filters"}</h3><p>{isInvestigator ? "When a reporter submits a case, it will appear here for review." : isReporter ? "Clear a filter or start a new report to get started." : "No cases are available for this filter. Clear filters to continue."}</p>{canSubmit && <Link href="/report/new" className="button button-primary">Create a report</Link>}</div> : <>
        <div className="table-wrap"><table className="data-table"><thead><tr><th>CASE</th><th>STATUS</th><th>EVIDENCE</th><th>AI LEADS</th><th>INTEGRITY CHECK</th><th>CREATED</th><th aria-label="Open" /></tr></thead><tbody>
          {items.map((item) => <tr key={item.id}><td><Link className="case-title-link" href={`/cases/${item.id}`}><span className="case-ref">{item.case_ref}</span><strong>{item.title}</strong></Link></td><td><span className={`status-chip status-${item.status}`}>{titleCase(item.status)}</span></td><td><strong>{item.evidence_count}</strong><span className="table-secondary"> {item.pending_count ? `· ${item.pending_count} pending` : "files"}</span></td><td>{item.threat_count ? <span className="lead-count">{item.threat_count} <span>review</span></span> : <span className="table-secondary">None</span>}</td><td><VerifyBadge compact result={item.verification} /></td><td>{formatDate(item.created_at, { timeStyle: undefined })}</td><td><Link className="row-open" aria-label={`${isInvestigator ? "Open review for" : "Open"} ${item.case_ref}`} href={`/cases/${item.id}`}>{isInvestigator ? <span className="row-open-label">Open review</span> : "→"}</Link></td></tr>)}
        </tbody></table></div>
        <div className="table-pagination"><span>Showing {Math.min((page - 1) * pageSize + 1, total)}–{Math.min(page * pageSize, total)} of {total}</span><div><button className="button button-subtle" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</button><span className="page-number">{page} / {maxPage}</span><button className="button button-subtle" disabled={page >= maxPage} onClick={() => setPage((value) => Math.min(maxPage, value + 1))}>Next</button></div></div>
      </>}
    </section>
    <p className="note-line"><span>ⓘ</span> A Verified check means the file is unchanged since anchoring. It does not say who created it or whether its contents are accurate.</p>
  </>;
}
