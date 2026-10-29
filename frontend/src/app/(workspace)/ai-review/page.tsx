"use client";

import { useEffect, useState } from "react";
import { ApiError, getReviewInsights } from "@/lib/api";
import { titleCase } from "@/lib/format";
import type { ReviewInsightBucket, ReviewInsights } from "@/lib/types";
import { useSessionUser } from "@/lib/session";

function FeedbackTable({ title, description, rows }: { title: string; description: string; rows: ReviewInsightBucket[] }) {
  return <section className="panel review-insight-panel">
    <div className="panel-title-row"><div><h2>{title}</h2><p>{description}</p></div><span className="count-pill">{rows.reduce((sum, row) => sum + row.total, 0)} reviewed</span></div>
    {rows.length === 0 ? <div className="compact-empty"><p>No reviewed flags in this breakdown yet.</p></div> : <div className="table-wrap"><table className="data-table"><thead><tr><th>GROUP</th><th>CONFIRMED</th><th>REJECTED</th><th>TOTAL</th></tr></thead><tbody>{rows.map((row) => <tr key={row.label}><td><strong>{titleCase(row.label)}</strong></td><td>{row.confirmed}</td><td>{row.rejected}</td><td>{row.total}</td></tr>)}</tbody></table></div>}
  </section>;
}

export default function AiReviewInsightsPage() {
  const user = useSessionUser();
  const authorized = ["investigator", "legal", "admin"].includes(user?.role || "");
  const [insights, setInsights] = useState<ReviewInsights | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!authorized) return;
    let active = true;
    getReviewInsights().then((result) => { if (active) setInsights(result); })
      .catch((reason: unknown) => setError(reason instanceof ApiError ? reason.message : "Could not load review insights."))
      .finally(() => setLoading(false));
    return () => { active = false; };
  }, [authorized]);

  if (!authorized) return <div className="inline-error" role="alert"><strong>Review insights are restricted</strong><span>Review insights are limited to investigator, legal, and admin roles.</span></div>;

  return <>
    <div className="page-heading"><div><div className="eyebrow">HUMAN REVIEW</div><h1>Review insights</h1><p>See how reviewers have classified AI-generated flags so far.</p></div></div>
    {error && authorized && <div className="form-error" role="alert">{error}</div>}
    {loading ? <div className="table-state"><div className="spinner" /><span>Loading reviewer feedback…</span></div> : insights && <>
      <div className="detail-metrics review-insight-metrics">
        <article className="stat-card metric-wide"><span className="metric-label">REVIEWED FLAGS</span><strong>{insights.reviewed_flag_count}</strong></article>
        <article className="stat-card metric-wide"><span className="metric-label">CONFIRMED BY REVIEWERS</span><strong>{insights.outcomes.confirmed}</strong></article>
        <article className="stat-card metric-wide"><span className="metric-label">REJECTED BY REVIEWERS</span><strong>{insights.outcomes.rejected}</strong></article>
      </div>
      {insights.reviewed_flag_count === 0 ? <section className="panel"><div className="empty-state"><div className="empty-icon">◷</div><h3>No reviewer feedback yet</h3><p>After an investigator confirms or rejects an AI flag, feedback counts will appear here.</p></div></section> : <div className="review-insights-grid">
        <FeedbackTable title="By category" description="Reviewer decisions grouped by flagged category." rows={insights.by_category} />
        <FeedbackTable title="By language" description="Language recorded for the analyzed evidence." rows={insights.by_language} />
        <FeedbackTable title="By media type" description="File type of evidence associated with each reviewed flag." rows={insights.by_media_type} />
        <FeedbackTable title="By review reason" description="Structured reason selected when a reviewer made a decision." rows={insights.by_review_reason} />
      </div>}
      <div className="split-note review-insight-caveat"><div className="notice-icon">i</div><div><p><strong>These counts are reviewer feedback, not model accuracy.</strong></p><ul>{insights.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div></div>
    </>}
  </>;
}
