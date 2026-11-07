"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError, getAudit, verifyAudit } from "@/lib/api";
import { formatDate, shortHash, titleCase } from "@/lib/format";
import type { AuditEntry } from "@/lib/types";
import { useSessionUser } from "@/lib/session";

const PAGE_SIZE = 50;

export default function AuditPage() {
  const user = useSessionUser();
  const authorized = user?.role === "legal" || user?.role === "admin";
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [caseDraft, setCaseDraft] = useState("");
  const [targetDraft, setTargetDraft] = useState("");
  const [filters, setFilters] = useState({ caseId: "", targetId: "" });
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [chainResult, setChainResult] = useState<{ valid: boolean; entries_checked: number; failed_entry_id?: string | null } | null>(null);
  const [checking, setChecking] = useState(false);

  const loadEntries = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setEntries(await getAudit({ ...filters, limit: PAGE_SIZE, offset }));
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Could not load the audit trail.");
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }, [filters, offset]);

  useEffect(() => {
    if (authorized) void loadEntries();
  }, [authorized, loadEntries, refresh]);

  async function checkChain() {
    setChecking(true);
    setError("");
    try {
      setChainResult(await verifyAudit());
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "The audit chain could not be checked.");
    } finally {
      setChecking(false);
    }
  }

  function applyFilters() {
    setOffset(0);
    setFilters({ caseId: caseDraft.trim(), targetId: targetDraft.trim() });
  }

  function clearFilters() {
    setCaseDraft("");
    setTargetDraft("");
    setOffset(0);
    setFilters({ caseId: "", targetId: "" });
  }

  if (!authorized) return <div className="inline-error" role="alert"><strong>Audit access is restricted</strong><span>Audit access is limited to legal and admin roles.</span></div>;

  return <>
    <div className="page-heading heading-row">
      <div><div className="eyebrow">GOVERNANCE</div><h1>Audit trail</h1><p>Append-only history of case and evidence actions. The API enforces access for legal and admin roles.</p></div>
      <div className="heading-actions">
        <button className="button button-subtle" onClick={() => setRefresh((value) => value + 1)} disabled={loading}>Refresh events</button>
        <button className="button button-primary" onClick={checkChain} disabled={checking}>{checking ? "Checking chain…" : "Verify audit chain"}<span aria-hidden="true">↻</span></button>
      </div>
    </div>
    {chainResult && <div className={`chain-result ${chainResult.valid ? "chain-valid" : "chain-invalid"}`} role="status"><strong>{chainResult.valid ? "Audit chain valid" : "Audit chain issue found"}</strong><span>{chainResult.entries_checked} entries checked{chainResult.failed_entry_id ? ` · problem at ${shortHash(chainResult.failed_entry_id, 8)}` : ""}</span></div>}
    {error && <div className="form-error" role="alert">{error}</div>}
    <section className="panel">
      <div className="panel-title-row"><div><h2>Recorded events</h2><p>Newest events appear first. Times use the browser’s local timezone.</p></div><span className="count-pill">{entries.length} events on this page</span></div>
      <form className="filter-grid audit-filters" onSubmit={(event) => { event.preventDefault(); applyFilters(); }}>
        <label><span className="sr-only">Filter by case ID</span><input value={caseDraft} onChange={(event) => setCaseDraft(event.target.value)} placeholder="Filter by case ID" /></label>
        <label><span className="sr-only">Filter by target ID</span><input value={targetDraft} onChange={(event) => setTargetDraft(event.target.value)} placeholder="Filter by evidence or target ID" /></label>
        <button className="button button-primary" type="submit">Apply filters</button>
        <button className="button button-subtle filter-clear" type="button" onClick={clearFilters}>Clear</button>
      </form>
      {loading ? <div className="table-state"><div className="spinner" /><span>Loading audit events…</span></div> : entries.length === 0 ? <div className="empty-state"><div className="empty-icon">≋</div><h3>{filters.caseId || filters.targetId ? "No matching events" : "No audit events available"}</h3><p>{filters.caseId || filters.targetId ? "Check the identifier and try again." : "Audit records appear as users interact with cases and evidence."}</p></div> : <>
        <div className="table-wrap"><table className="data-table audit-table"><thead><tr><th>SEQUENCE</th><th>EVENT</th><th>ACTOR ROLE</th><th>CASE / TARGET</th><th>ENTRY HASH</th><th>TIME</th></tr></thead><tbody>{entries.map((entry) => <tr key={entry.id}>
          <td><code>#{entry.seq}</code></td>
          <td><strong>{titleCase(entry.action)}</strong><small>{entry.target_type}</small>{Object.keys(entry.details || {}).length > 0 && <details className="audit-details"><summary>Event details</summary><pre>{JSON.stringify(entry.details, null, 2)}</pre></details>}</td>
          <td>{entry.actor_role ? <span className="role-pill">{entry.actor_role}</span> : "System"}</td>
          <td>{entry.case_id ? <Link className="text-link" href={`/cases/${entry.case_id}`}>{shortHash(entry.case_id, 6)}</Link> : "—"}<small>{entry.target_id ? shortHash(entry.target_id, 8) : "No target ID"}</small></td>
          <td><code title={entry.entry_hash}>{shortHash(entry.entry_hash, 8)}</code></td>
          <td title={new Date(entry.created_at).toISOString()}>{formatDate(entry.created_at)}</td>
        </tr>)}</tbody></table></div>
        <div className="table-pagination"><span>Showing {offset + 1}–{offset + entries.length} events</span><div><button className="button button-subtle" disabled={offset === 0 || loading} onClick={() => setOffset((value) => Math.max(0, value - PAGE_SIZE))}>Previous</button><span className="page-number">{Math.floor(offset / PAGE_SIZE) + 1}</span><button className="button button-subtle" disabled={entries.length < PAGE_SIZE || loading} onClick={() => setOffset((value) => value + PAGE_SIZE)}>Next</button></div></div>
      </>}
    </section>
    <div className="split-note"><div className="notice-icon">i</div><p><strong>Audit events are sensitive.</strong><br />The server enforces role permissions. Event details can include operational context; share exports only with authorized reviewers.</p></div>
  </>;
}
