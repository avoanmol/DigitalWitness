"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, downloadReport, getCase, getCaseActivity, getCaseInvestigationSummary } from "@/lib/api";
import { formatBytes, formatDate, shortHash, titleCase } from "@/lib/format";
import type { CaseActivityEvent, CaseDetail, CaseInvestigationSummary } from "@/lib/types";
import { VerifyBadge } from "@/components/verify-badge";
import { useSessionUser } from "@/lib/session";

export default function CaseDetailPage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id);
  const role = useSessionUser()?.role || "";
  const canReview = ["investigator", "legal", "admin"].includes(role);
  const [item, setItem] = useState<CaseDetail | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [reporting, setReporting] = useState(false);
  const [reportError, setReportError] = useState("");
  const [activity, setActivity] = useState<CaseActivityEvent[]>([]);
  const [activityCaseId, setActivityCaseId] = useState("");
  const [activityLoading, setActivityLoading] = useState(true);
  const [activityError, setActivityError] = useState("");
  const [investigationSummary, setInvestigationSummary] = useState<CaseInvestigationSummary | null>(null);
  const [summaryCaseId, setSummaryCaseId] = useState("");
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState("");
  const activityPending = activityLoading || activityCaseId !== id;
  const summaryPending = summaryLoading || (canReview && summaryCaseId !== id);

  useEffect(() => {
    getCase(id).then(setItem).catch((reason: unknown) => setError(reason instanceof ApiError ? reason.message : "Could not load this case.")).finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!canReview) return;
    let active = true;
    getCaseInvestigationSummary(id)
      .then((summary) => { if (active) { setInvestigationSummary(summary); setSummaryCaseId(id); setSummaryError(""); } })
      .catch((reason: unknown) => {
        if (active) { setSummaryCaseId(id); setSummaryError(reason instanceof ApiError ? reason.message : "The case overview could not be loaded."); }
      })
      .finally(() => { if (active) setSummaryLoading(false); });
    return () => { active = false; };
  }, [canReview, id]);

  useEffect(() => {
    let active = true;
    getCaseActivity(id)
      .then((events) => { if (active) { setActivity(events); setActivityCaseId(id); setActivityError(""); } })
      .catch((reason: unknown) => {
        if (active) { setActivityCaseId(id); setActivityError(reason instanceof ApiError ? reason.message : "The activity feed could not be loaded."); }
      })
      .finally(() => { if (active) setActivityLoading(false); });
    return () => { active = false; };
  }, [id]);

  async function report() {
    if (!item) return;
    setReporting(true); setReportError("");
    try { await downloadReport(item.id, item.case_ref); }
    catch (reason) { setReportError(reason instanceof ApiError ? reason.message : "The report could not be generated."); }
    finally { setReporting(false); }
  }

  if (loading) return <div className="table-state"><div className="spinner" /><span>Loading case…</span></div>;
  if (error || !item) return <div className="page-heading"><Link className="back-link" href="/cases">← All cases</Link><div className="inline-error" role="alert"><strong>Case is unavailable</strong><span>{error || "This case could not be found."}</span></div></div>;
  const latest = item.evidence.map((evidence) => evidence.verification).find((result) => result === "altered") || item.evidence.map((evidence) => evidence.verification).find((result) => result === "pending") || item.evidence[0]?.verification || null;

  return <>
    <div className="detail-back"><Link className="back-link" href="/cases">← {role === "investigator" ? "Investigation desk" : "Case workspace"}</Link></div>
    <div className="page-heading detail-heading"><div><div className="eyebrow">{item.case_ref} <span>·</span> {titleCase(item.status)}</div><h1>{item.title}</h1><p>{item.description || "No case description has been added."}</p></div><div className="heading-actions">{role === "reporter" && <Link className="button button-primary" href={`/cases/${item.id}/complaint`}>Prepare complaint draft <span>→</span></Link>}{["investigator", "admin"].includes(role) && <Link className="button button-subtle" href={`/cases/${item.id}/links`}>Review findings & related cases <span>↗</span></Link>}{["legal", "admin"].includes(role) && <button className="button button-primary" onClick={report} disabled={reporting}>{reporting ? "Preparing report…" : "Download review report"}<span>↓</span></button>}</div></div>
    {reportError && <div className="form-error" role="alert">{reportError}</div>}
    {role === "reporter" && <div className="split-note"><div className="notice-icon">i</div><p><strong>Prepare a complaint when you are ready</strong><br />You control the details, review the evidence and AI notes, and choose whether to download a draft. DigitalWitness will not submit it for you.</p></div>}
    {role === "investigator" && <nav className="investigator-workflow" aria-label="Case review steps"><span className="workflow-label">REVIEW THIS REPORT</span><a href="#case-activity"><b>1</b> Timeline</a><a href="#case-evidence"><b>2</b> Original evidence</a><a href="#case-ai-review"><b>3</b> AI leads</a><Link href={`/cases/${item.id}/links`}><b>4</b> Related cases</Link><button type="button" onClick={report} disabled={reporting}><b>5</b> {reporting ? "Preparing report…" : "Create review report"}</button></nav>}
    <section className="detail-metrics"><div className="panel metric-wide"><span className="stat-label">Case status</span><strong>{titleCase(item.status)}</strong><span className="stat-foot">Created {formatDate(item.created_at)}</span></div><div className="panel metric-wide"><span className="stat-label">Evidence files</span><strong>{item.evidence.length}</strong><span className="stat-foot">Read-only after submission</span></div><div className="panel metric-wide"><span className="stat-label">AI suggestions</span><strong>{item.threat_count}</strong><span className="stat-foot">Review required before action</span></div><div className="panel metric-wide"><span className="stat-label">Latest integrity check</span><VerifyBadge compact result={latest} /></div></section>
    {["investigator", "legal", "admin"].includes(role) && <section id="case-ai-review" className="panel case-investigation-panel">
      <div className="panel-title-row"><div><span className="eyebrow">CASE-WIDE REVIEW</span><h2>Investigative overview</h2><p>Source-linked rollup of saved analysis and human review status.</p></div>{investigationSummary && <span className="activity-count">Generated {formatDate(investigationSummary.generated_at)}</span>}</div>
      {summaryPending ? <div className="table-state"><div className="spinner" /><span>Building case overview…</span></div>
        : summaryError ? <div className="activity-empty" role="status">Overview is unavailable. {summaryError}</div>
        : investigationSummary ? <>
          <div className="investigation-summary"><span className="summary-label">DETERMINISTIC CASE ROLLUP</span><p>{investigationSummary.overview}</p></div>
          {investigationSummary.categories.length > 0 && <div className="case-category-rollup">{investigationSummary.categories.map((category) => <article className="case-category-card" key={category.category}>
            <strong>{titleCase(category.category)}</strong><span>Reporter focus: {category.focus_evidence_ids.length} file{category.focus_evidence_ids.length === 1 ? "" : "s"} · AI flags: {category.flag_evidence_ids.length} file{category.flag_evidence_ids.length === 1 ? "" : "s"}</span><small>{category.pending_count} pending · {category.confirmed_count} confirmed · {category.rejected_count} rejected flags</small>
          </article>)}</div>}
          <div className="case-source-list">{investigationSummary.evidence.map((source) => <article className="case-source-card" key={source.evidence_id}>
            <div className="case-source-heading"><Link href={`/evidence/${source.evidence_id}`}><strong>{source.filename}</strong><span>Open source ↗</span></Link><span className={`status-chip status-${source.analysis_status}`}>{titleCase(source.analysis_status)}</span></div>
            <p>{source.language ? `Detected language: ${source.language}. ` : "Language not established. "}{source.extraction_method ? `Extraction: ${source.extraction_method}.` : "No extraction method recorded."}</p>
            {source.coverage?.notes?.length ? <ul className="observation-list">{source.coverage.notes.map((note) => <li key={note}>{note}</li>)}</ul> : null}
            {source.flags.length > 0 && <ul className="case-source-flags">{source.flags.map((flag) => <li key={flag.id}><span className={`review-status review-${flag.review_status}`}>{titleCase(flag.review_status)}</span><b>{titleCase(flag.category)}</b><span>“{flag.snippet}”</span>{flag.review_reason && <small>Review reason: {titleCase(flag.review_reason.replaceAll("_", " "))}</small>}</li>)}</ul>}
          </article>)}</div>
          <ul className="case-summary-limitations">{investigationSummary.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
        </> : <div className="activity-empty">No case overview is available.</div>}
    </section>}
    <section id="case-activity" className="panel activity-panel" aria-labelledby="activity-heading">
      <div className="panel-title-row"><div><h2 id="activity-heading">Case activity</h2><p>Recorded evidence and review milestones.</p></div>{!activityPending && !activityError && <span className="activity-count">{activity.length} {activity.length === 1 ? "event" : "events"}</span>}</div>
      {activityPending ? <div className="table-state"><div className="spinner" /><span>Loading case activity…</span></div>
        : activityError ? <div className="activity-empty" role="status">Activity is temporarily unavailable. {activityError}</div>
        : activity.length === 0 ? <div className="activity-empty">No activity has been recorded yet.</div>
        : <ol className="activity-feed">{activity.map((event) => <li className="activity-event" key={event.id}>
          <span className="activity-marker" aria-hidden="true" />
          <div className="activity-event-content"><div className="activity-event-heading"><strong>{event.title}</strong><time dateTime={event.created_at} title={`${event.created_at} (UTC)`}>{formatDate(event.created_at)}</time></div>
            <p>{event.description}</p><span className="activity-actor">{titleCase(event.actor_role || "system")}</span>
          </div>
        </li>)}</ol>}
    </section>
    <section id="case-evidence" className="panel evidence-panel"><div className="panel-title-row"><div><h2>Evidence in this case</h2><p>Original fingerprints and anchor state.</p></div><Link className="button button-subtle" href={`/cases/${item.id}/links`}>Review AI findings & related cases <span>→</span></Link></div>
      {item.evidence.length === 0 ? <div className="empty-state compact-empty"><div className="empty-icon">▤</div><h3>No evidence submitted yet</h3><p>{role === "investigator" ? "The reporter has not submitted any files yet." : "No evidence has been submitted to this case yet."}</p>{role === "reporter" && <Link className="button button-primary" href="/report/new">Submit evidence</Link>}</div> : <div className="table-wrap"><table className="data-table"><thead><tr><th>FILE</th><th>SHA-256</th><th>SIZE</th><th>STATUS</th><th>VERIFICATION</th><th>UPLOADED</th><th /></tr></thead><tbody>{item.evidence.map((evidence) => <tr key={evidence.id}><td><Link className="evidence-title-link" href={`/evidence/${evidence.id}`}><span className="file-type-icon">▤</span><span><strong>{evidence.filename}</strong><small>{evidence.mime_type}</small></span></Link></td><td><code title={evidence.sha256}>{shortHash(evidence.sha256, 8)}</code></td><td>{formatBytes(evidence.size_bytes)}</td><td><span className={`status-chip status-${evidence.status}`}>{titleCase(evidence.status)}</span></td><td><VerifyBadge compact result={evidence.verification} /></td><td>{formatDate(evidence.uploaded_at)}</td><td><Link className="row-open" href={`/evidence/${evidence.id}`} aria-label={`Open ${evidence.filename}`}>→</Link></td></tr>)}</tbody></table></div>}
    </section>
    <div className="split-note"><div className="notice-icon">i</div><p><strong>What this check means</strong><br />Verified means the file is unchanged since anchoring. It does not establish who created the file or whether its contents are accurate.</p></div>
  </>;
}
