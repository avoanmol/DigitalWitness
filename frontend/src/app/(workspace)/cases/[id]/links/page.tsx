"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { ApiError, createLink, getAnalysis, getCase, getCases, getLinks, requestAnalysis, updateFlag, updateLink } from "@/lib/api";
import { titleCase } from "@/lib/format";
import type { CaseDetail, CaseLink, CaseSummary, EvidenceSummary, FlagReviewReason, LinkReviewReason, ThreatFlag } from "@/lib/types";
import { useSessionUser } from "@/lib/session";

type AnalysisRow = { evidence: EvidenceSummary; status: string; error?: string };

const FLAG_REVIEW_REASONS: { value: FlagReviewReason; label: string }[] = [
  { value: "source_supports_flag", label: "Source supports this flag" },
  { value: "reported_or_quoted_context", label: "Reported or quoted context" },
  { value: "educational_or_hypothetical_context", label: "Educational or hypothetical context" },
  { value: "wrong_category", label: "Wrong category" },
  { value: "snippet_not_supported", label: "Snippet not supported by source" },
  { value: "extraction_unclear", label: "OCR or extraction unclear" },
  { value: "duplicate_or_repeated", label: "Duplicate or repeated flag" },
  { value: "insufficient_context", label: "Not enough context" },
  { value: "other", label: "Other" },
];

const LINK_REVIEW_REASONS: { value: LinkReviewReason; label: string }[] = [
  { value: "source_supports_connection", label: "Evidence supports a meaningful connection" },
  { value: "shared_identifier_is_common", label: "The shared detail is common or inconclusive" },
  { value: "different_account_or_person", label: "The accounts or people appear different" },
  { value: "separate_context", label: "The reports have separate context" },
  { value: "insufficient_context", label: "Not enough context to decide" },
  { value: "other", label: "Other reason" },
];

function analysisMessage(status: string) {
  if (status === "pending" || status === "running") return "Analysis is in the background queue.";
  if (status === "failed") return "Analysis failed. An investigator can retry it.";
  if (status === "skipped") return "No usable text was extracted. Review the original and extraction coverage; retry after addressing any missing OCR support.";
  if (status === "done") return "Analysis finished. Review any flags and suggested links below.";
  return "Analysis status is unavailable.";
}

export default function CaseLinksPage() {
  const params = useParams<{ id: string }>();
  const caseId = decodeURIComponent(params.id);
  const role = useSessionUser()?.role || "";
  const authorized = ["investigator", "legal", "admin"].includes(role);
  const [item, setItem] = useState<CaseDetail | null>(null);
  const [links, setLinks] = useState<CaseLink[]>([]);
  const [flags, setFlags] = useState<ThreatFlag[]>([]);
  const [analysisRows, setAnalysisRows] = useState<AnalysisRow[]>([]);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [otherId, setOtherId] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshCount, setRefreshCount] = useState(0);
  const [saving, setSaving] = useState("");
  const [flagReviewReasons, setFlagReviewReasons] = useState<Record<string, FlagReviewReason | "">>({});
  const [linkReviewReasons, setLinkReviewReasons] = useState<Record<string, LinkReviewReason | "">>({});

  useEffect(() => {
    let alive = true;
    let timer: number | undefined;
    let polls = 0;
    if (!authorized) return () => { alive = false; };

    async function load() {
      try {
        const [caseResult, linksResult, casesResult] = await Promise.all([
          getCase(caseId),
          getLinks(caseId),
          getCases({ page_size: 100 }),
        ]);
        const results = await Promise.allSettled(caseResult.evidence.map((evidence) => getAnalysis(evidence.id)));
        if (!alive) return;
        const rows: AnalysisRow[] = results.map((result, index) => ({
          evidence: caseResult.evidence[index],
          status: result.status === "fulfilled" ? result.value.status : caseResult.evidence[index].analysis_status,
          error: result.status === "rejected" ? "Analysis details could not be loaded." : undefined,
        }));
        setItem(caseResult);
        setLinks(linksResult);
        setCases(casesResult.items.filter((candidate) => candidate.id !== caseId));
        setAnalysisRows(rows);
        setFlags(results.flatMap((result) => result.status === "fulfilled" ? result.value.flags : []));
        setError("");
        const pending = rows.some((row) => row.status === "pending" || row.status === "running");
        const waitingForLinkJob = rows.length > 0 && polls < 5;
        if ((pending && polls < 24) || waitingForLinkJob) {
          polls += 1;
          timer = window.setTimeout(load, pending ? 3000 : 2000);
        }
      } catch (reason) {
        if (alive) setError(reason instanceof ApiError ? reason.message : "Could not load the review queue.");
      } finally {
        if (alive) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    }
    void load();
    return () => {
      alive = false;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [authorized, caseId, refreshCount]);

  function refreshResults() {
    setRefreshing(true);
    setRefreshCount((count) => count + 1);
  }

  async function retryAnalysis(evidenceId: string) {
    setSaving(evidenceId);
    setError("");
    try {
      await requestAnalysis(evidenceId);
      setAnalysisRows((current) => current.map((row) => row.evidence.id === evidenceId ? { ...row, status: "pending", error: undefined } : row));
      setRefreshCount((count) => count + 1);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Could not queue analysis.");
    } finally {
      setSaving("");
    }
  }

  async function reviewLink(id: string, status: "confirmed" | "rejected") {
    const review_reason = linkReviewReasons[id];
    if (!review_reason) {
      setError("Choose a reason before saving this connection decision.");
      return;
    }
    setSaving(id);
    setError("");
    try {
      await updateLink(id, status, review_reason);
      setLinks((current) => current.map((link) => link.id === id ? { ...link, status, review_reason } : link));
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Could not save link review.");
    } finally {
      setSaving("");
    }
  }

  async function reviewFlag(flag: ThreatFlag, review_status: "confirmed" | "rejected") {
    const review_reason = flagReviewReasons[flag.id];
    if (!review_reason) {
      setError("Choose a review reason before saving this label.");
      return;
    }
    setSaving(flag.id);
    setError("");
    try {
      await updateFlag(flag.id, review_status, review_reason);
      setFlags((current) => current.map((candidate) => candidate.id === flag.id ? { ...candidate, review_status, review_reason } : candidate));
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Could not save flag review.");
    } finally {
      setSaving("");
    }
  }

  async function addLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!otherId) return;
    setSaving("manual");
    setError("");
    try {
      await createLink(caseId, otherId, note.trim());
      const [refreshed, allCases] = await Promise.all([getLinks(caseId), getCases({ page_size: 100 })]);
      setLinks(refreshed);
      setCases(allCases.items.filter((candidate) => candidate.id !== caseId));
      setNote("");
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Could not add the link.");
    } finally {
      setSaving("");
    }
  }

  if (!authorized) return <div className="inline-error" role="alert"><strong>Review access is restricted</strong><span>Only investigators, legal and admins can view this review queue. The API must authorize each action as well.</span><Link className="button button-subtle" href={"/cases/" + caseId}>Back to case</Link></div>;
  if (loading) return <div className="table-state"><div className="spinner" /><span>Loading review queue…</span></div>;
  if (error && !item) return <div className="inline-error" role="alert"><strong>Review queue unavailable</strong><span>{error}</span><Link className="button button-subtle" href="/cases">Back to cases</Link></div>;
  if (!item) return null;
  const pendingFlags = flags.filter((flag) => flag.review_status === "pending").length;
  const pendingLinks = links.filter((link) => link.status === "suggested").length;
  const pendingAnalyses = analysisRows.filter((row) => row.status === "pending" || row.status === "running").length;

  return <>
    <div className="detail-back"><Link className="back-link" href={"/cases/" + caseId}>← {item.case_ref}</Link></div>
      <div className="page-heading heading-row">
      <div><div className="eyebrow">HUMAN REVIEW <span>·</span> {item.case_ref}</div><h1>Review findings and related cases</h1><p>Check each AI suggestion against the original evidence and surrounding context. You decide whether it matters.</p></div>
      <div className="heading-actions"><span className="count-pill review-count">{pendingLinks + pendingFlags} pending review</span><button className="button button-subtle" type="button" onClick={refreshResults} disabled={refreshing}>{refreshing ? "Refreshing…" : "Refresh results"}</button></div>
    </div>
    {pendingAnalyses > 0 && <p className="note-line"><span>◷</span> {pendingAnalyses} evidence {pendingAnalyses === 1 ? "file is" : "files are"} still being analysed.</p>}
    {error && <div className="form-error" role="alert">{error}</div>}

    <section className="panel review-section">
      <div className="panel-title-row"><div><span className="eyebrow">EVIDENCE ANALYSIS</span><h2>Processing status</h2><p>Uploads enter a background queue; failed analysis can be retried.</p></div><span className="count-pill">{analysisRows.length} files</span></div>
      {analysisRows.length === 0 ? <div className="empty-state compact-empty"><div className="empty-icon">▤</div><h3>No evidence to analyse</h3><p>Upload evidence to start entity extraction and link suggestions.</p></div> : <div className="review-card-list">{analysisRows.map((row) => <article className="review-card" key={row.evidence.id}>
        <div className="review-card-main"><div className="review-topline"><Link className="case-title-link" href={`/evidence/${row.evidence.id}`}><strong>{row.evidence.filename} · Open original ↗</strong></Link><span className={"review-status review-" + row.status}>{titleCase(row.status)}</span></div><p>{row.error || analysisMessage(row.status)}</p></div>
        {["investigator", "admin"].includes(role) && (row.status === "failed" || row.status === "skipped") && <div className="review-actions"><button className="button button-subtle" type="button" disabled={saving === row.evidence.id} onClick={() => retryAnalysis(row.evidence.id)}>{saving === row.evidence.id ? "Queuing…" : "Retry analysis"}</button></div>}
      </article>)}</div>}
    </section>

    <section className="panel review-section">
      <div className="panel-title-row"><div><span className="eyebrow">CASE LINKS</span><h2>Related reports</h2><p>Shared details and a heuristic match score are shown to support review.</p></div><span className="count-pill">{links.length} suggestions</span></div>
      {links.length === 0 ? <div className="empty-state compact-empty"><div className="empty-icon">↗</div><h3>No suggested links yet</h3><p>Shared entities will appear here when analysis is available.</p></div> : <div className="review-card-list">{links.map((link) => <article className="review-card" key={link.id}>
        <div className="review-card-main"><div className="review-topline"><span className="ai-label"><span>✳</span> AI SUGGESTION</span><span className={"review-status review-" + link.status}>{titleCase(link.status)}</span></div>
          <h3><Link href={"/cases/" + (link.case_a_id === caseId ? link.case_b_id : link.case_a_id)}>{link.other_case_ref} · {link.other_case_title} <span>↗</span></Link></h3>
          <div className="shared-entity-list">{link.shared_entities.map((entity) => <span key={entity.id} className="entity-chip"><b>{titleCase(entity.type)}</b>{entity.raw}</span>)}</div>
          <div className="confidence-line"><span>Match score</span><div className="confidence-track"><i style={{ width: Math.round(link.confidence * 100) + "%" }} /></div><strong>{Math.round(link.confidence * 100)}%</strong></div>
        </div>
        <div className="review-actions">{["investigator", "admin"].includes(role) && (link.status === "suggested" ? <><label className="review-feedback-label">Reason for decision<select aria-label={`Reason for related-case decision ${link.other_case_ref}`} value={linkReviewReasons[link.id] || ""} onChange={(event) => setLinkReviewReasons((current) => ({ ...current, [link.id]: event.target.value as LinkReviewReason | "" }))}><option value="">Choose a reason</option>{LINK_REVIEW_REASONS.map((reason) => <option key={reason.value} value={reason.value}>{reason.label}</option>)}</select></label><div><button className="button button-confirm" disabled={saving === link.id || !linkReviewReasons[link.id]} onClick={() => reviewLink(link.id, "confirmed")}>✓ Confirm connection</button><button className="button button-reject" disabled={saving === link.id || !linkReviewReasons[link.id]} onClick={() => reviewLink(link.id, "rejected")}>× Reject connection</button></div></> : <span className="reviewed-note">Decision recorded · {LINK_REVIEW_REASONS.find((reason) => reason.value === link.review_reason)?.label || "reason not recorded"}</span>)}</div>
      </article>)}</div>}
      {role === "legal" && <div className="read-only-note">Legal role: read-only review access.</div>}
      {["investigator", "admin"].includes(role) && <form className="manual-link-form" onSubmit={addLink}><div><strong>Manually add a case link</strong><span>Optional. Add a note to explain why these reports may be related.</span></div><select aria-label="Related case" value={otherId} onChange={(event) => setOtherId(event.target.value)}><option value="">Choose a case</option>{cases.map((candidate) => <option value={candidate.id} key={candidate.id}>{candidate.case_ref} — {candidate.title}</option>)}</select><input value={note} onChange={(event) => setNote(event.target.value)} maxLength={1000} aria-label="Link note" placeholder="Short review note (optional)" /><button className="button button-subtle" disabled={!otherId || saving === "manual"}>{saving === "manual" ? "Adding…" : "Add link"}</button></form>}
    </section>

    <section className="panel review-section flags-section">
      <div className="panel-title-row"><div><span className="eyebrow">THREAT FLAGS</span><h2>Items for review</h2><p>Snippets are displayed as plain text from the analysis result.</p></div><span className="count-pill">{flags.length} flags</span></div>
      {flags.length === 0 ? <div className="empty-state compact-empty"><div className="empty-icon">✳</div><h3>No flags returned</h3><p>Analysis results will appear here when they are available.</p></div> : <div className="flag-grid">{flags.map((flag) => <article className={"flag-card severity-" + flag.severity} key={flag.id}>
        <div className="flag-topline"><span className={"severity-tag severity-tag-" + flag.severity}>{titleCase(flag.severity)} severity</span><span className="ai-label"><span>✳</span> AI SUGGESTION</span></div><h3>{titleCase(flag.threat_class)}</h3>{analysisRows.find((row) => row.evidence.id === flag.evidence_id) && <Link className="external-link" href={`/evidence/${flag.evidence_id}`}>Open original source and full context ↗</Link>}<blockquote>“{flag.snippet}”</blockquote>
        {flag.reason && <p className="analysis-muted">{flag.reason}</p>}
        {flag.review_reason && <p className="analysis-muted">Human review label: {titleCase(flag.review_reason.replaceAll("_", " "))}</p>}
        <div className="flag-confidence"><span>Uncalibrated review score</span><strong>{Math.round(flag.confidence * 100)}%</strong><span className={"review-status review-" + flag.review_status}>{titleCase(flag.review_status)}</span></div>
        {flag.review_status === "pending" && ["investigator", "admin"].includes(role) && <div className="flag-actions review-feedback-actions"><label className="review-feedback-label">Why are you reviewing it this way?<select aria-label={`Review reason for ${titleCase(flag.threat_class)}`} value={flagReviewReasons[flag.id] || ""} onChange={(event) => setFlagReviewReasons((current) => ({ ...current, [flag.id]: event.target.value as FlagReviewReason | "" }))}><option value="">Choose a reason</option>{FLAG_REVIEW_REASONS.map((reason) => <option key={reason.value} value={reason.value}>{reason.label}</option>)}</select></label><div><button className="button button-confirm" disabled={saving === flag.id || !flagReviewReasons[flag.id]} onClick={() => reviewFlag(flag, "confirmed")}>✓ Confirm</button><button className="button button-reject" disabled={saving === flag.id || !flagReviewReasons[flag.id]} onClick={() => reviewFlag(flag, "rejected")}>× Reject</button></div></div>}
      </article>)}</div>}
    </section>
    <p className="note-line"><span>ⓘ</span> AI outputs are suggestions, not findings. Review the source evidence before making a decision.</p>
  </>;
}
