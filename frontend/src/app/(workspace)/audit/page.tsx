"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, getAudit, verifyAudit } from "@/lib/api";
import { formatDate, shortHash, titleCase } from "@/lib/format";
import type { AuditEntry } from "@/lib/types";
import { useSessionUser } from "@/lib/session";

export default function AuditPage() {
  const user = useSessionUser();
  const authorized = user?.role === "legal" || user?.role === "admin";
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  const [chainResult, setChainResult] = useState<{ valid: boolean; entries_checked: number; failed_entry_id?: string | null } | null>(null);
  const [checking, setChecking] = useState(false);
  useEffect(() => {
    if (!authorized) return;
    let active = true;
    getAudit().then((result) => { if (active) setEntries(result); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof ApiError ? reason.message : "Could not load the audit trail."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [authorized]);

  async function checkChain() {
    setChecking(true); setError("");
    try { setChainResult(await verifyAudit()); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : "The audit chain could not be checked."); }
    finally { setChecking(false); }
  }

  if (!authorized) return <div className="inline-error" role="alert"><strong>Audit access is restricted</strong><span>Audit access is limited to legal and admin roles.</span></div>;

  return <>
    <div className="page-heading heading-row"><div><div className="eyebrow">GOVERNANCE</div><h1>Audit trail</h1><p>Append-only history of case and evidence actions.</p></div><button className="button button-primary" onClick={checkChain} disabled={checking}>{checking ? "Checking chain…" : "Verify audit chain"}<span>↻</span></button></div>
    {chainResult && <div className={`chain-result ${chainResult.valid ? "chain-valid" : "chain-invalid"}`} role="status"><strong>{chainResult.valid ? "Audit chain valid" : "Audit chain issue found"}</strong><span>{chainResult.entries_checked} entries checked{chainResult.failed_entry_id ? ` · problem at ${shortHash(chainResult.failed_entry_id, 8)}` : ""}</span></div>}
    {error && <div className="form-error" role="alert">{error}</div>}
    <section className="panel"><div className="panel-title-row"><div><h2>Recorded events</h2><p>Times are displayed in IST; each entry hash is a chain link.</p></div><span className="count-pill">{entries.length} entries</span></div>
      {loading ? <div className="table-state"><div className="spinner" /><span>Loading audit events…</span></div> : entries.length === 0 ? <div className="empty-state"><div className="empty-icon">≋</div><h3>No audit events available</h3><p>Audit records appear as users interact with cases and evidence.</p></div> : <div className="table-wrap"><table className="data-table audit-table"><thead><tr><th>SEQUENCE</th><th>EVENT</th><th>ACTOR ROLE</th><th>CASE / TARGET</th><th>ENTRY HASH</th><th>TIME</th></tr></thead><tbody>{entries.map((entry) => <tr key={entry.id}><td><code>#{entry.seq}</code></td><td><strong>{titleCase(entry.action)}</strong><small>{entry.target_type}</small></td><td>{entry.actor_role ? <span className="role-pill">{entry.actor_role}</span> : "System"}</td><td>{entry.case_id ? <Link className="text-link" href={`/cases/${entry.case_id}`}>{shortHash(entry.case_id, 6)}</Link> : entry.target_id ? shortHash(entry.target_id, 8) : "—"}</td><td><code title={entry.entry_hash}>{shortHash(entry.entry_hash, 8)}</code></td><td title={new Date(entry.created_at).toISOString()}>{formatDate(entry.created_at)}</td></tr>)}</tbody></table></div>}
    </section>
    <div className="split-note"><div className="notice-icon">i</div><p><strong>Audit events are sensitive.</strong><br />Access is limited by role on the API. The interface only hides controls for clarity and does not replace server permissions.</p></div>
  </>;
}
