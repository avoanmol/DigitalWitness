"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, getAnalysis, getCase, getCases, getLinks, isMockMode } from "@/lib/api";
import { formatDate, titleCase } from "@/lib/format";
import type { CaseLink, CaseSummary, EvidenceSummary, ThreatFlag } from "@/lib/types";
import { useSessionUser } from "@/lib/session";

type FlagRow = { flag: ThreatFlag; evidence: EvidenceSummary; caseItem: CaseSummary };

export default function InsightsPage() {
  const user = useSessionUser();
  const authorized = ["investigator", "legal", "admin"].includes(user?.role || "");
  const [flags, setFlags] = useState<FlagRow[]>([]);
  const [links, setLinks] = useState<CaseLink[]>([]);
  const [loadedRefresh, setLoadedRefresh] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const loading = loadedRefresh !== refresh;

  useEffect(() => {
    if (!authorized) return;
    let active = true;
    async function load() {
      try {
        const page = await getCases({ page: 1, page_size: 100 });
        const details = await Promise.all(page.items.map(async (item) => {
          try { return await getCase(item.id); } catch { return null; }
        }));
        const validDetails = details.filter((item): item is NonNullable<typeof item> => item !== null);
        const analyses = await Promise.all(validDetails.flatMap((item) => item.evidence.map(async (evidence) => {
          try { return { evidence, caseItem: item, analysis: await getAnalysis(evidence.id) }; } catch { return null; }
        })));
        const caseLinks = await Promise.all(validDetails.map(async (item) => {
          try { return await getLinks(item.id); } catch { return []; }
        }));
        if (!active) return;
        setFlags(analyses.flatMap((row) => row ? row.analysis.flags.map((flag) => ({ flag, evidence: row.evidence, caseItem: row.caseItem })) : []));
        setLinks(Array.from(new Map(caseLinks.flat().map((link) => [link.id, link])).values()));
        setError("");
      } catch (reason) {
        if (active) setError(reason instanceof ApiError ? reason.message : "Could not load review insights.");
      } finally { if (active) setLoadedRefresh(refresh); }
    }
    void load();
    return () => { active = false; };
  }, [authorized, refresh]);

  const pending = flags.filter(({ flag }) => flag.review_status === "pending").length;
  const confirmed = flags.filter(({ flag }) => flag.review_status === "confirmed").length;
  const rejected = flags.filter(({ flag }) => flag.review_status === "rejected").length;
  const suggestedLinks = links.filter((link) => link.status === "suggested");
  const confirmedLinks = links.filter((link) => link.status === "confirmed");

  if (!authorized) return <div className="inline-error" role="alert"><strong>Review insights are restricted</strong><span>This cross-case view is available to investigator, legal, and admin roles.</span></div>;

  return <main className="pr-insights-page">
    <header className="pr-page-header"><div><p className="pr-eyebrow">REVIEW WORKSPACE / CROSS-CASE</p><h1>Review insights.</h1><p>AI-generated review leads and suggested connections across available cases.</p></div><button className="button button-subtle" onClick={() => setRefresh((value) => value + 1)} disabled={loading}>Refresh</button></header>
    {isMockMode() && <p className="pr-demo-note">Demo mode: figures are based on synthetic demonstration data.</p>}
    {error && <div className="inline-error" role="alert"><strong>Insights could not be loaded</strong><span>{error}</span><button className="button button-subtle" onClick={() => setRefresh((value) => value + 1)}>Try again</button></div>}
    {loading ? <div className="pr-reports-state" aria-live="polite">Loading review insights…</div> : <>
      <section className="pr-insight-section"><div className="pr-report-list-head"><div><p className="pr-eyebrow">AI REVIEW FLAGS</p><h2>Review status</h2></div><span>{flags.length} total</span></div>
        <div className="pr-report-metrics pr-insight-metrics"><Metric label="Total flags" value={flags.length} /><Metric label="Awaiting review" value={pending} /><Metric label="Confirmed" value={confirmed} /><Metric label="Rejected" value={rejected} /></div>
      </section>
      <section className="pr-insight-section"><div className="pr-report-list-head"><div><p className="pr-eyebrow">CASE CONNECTIONS</p><h2>Human review of suggested links</h2></div><span>{links.length} total</span></div>
        <div className="pr-report-metrics pr-insight-metrics pr-link-metrics"><Metric label="Suggested connections" value={suggestedLinks.length} /><Metric label="Confirmed connections" value={confirmedLinks.length} /></div>
        <div className="pr-insight-list">{links.length === 0 ? <Empty message="No case connections are available yet." /> : links.slice(0, 8).map((link) => <article className="pr-insight-row" key={link.id}><div><strong>{link.other_case_ref}</strong><p>{link.other_case_title}</p><small>{link.shared_entities.length} shared identifiers · {Math.round(link.confidence * 100)}% system score</small></div><span className={`status-chip status-${link.status}`}>{titleCase(link.status)}</span></article>)}</div>
      </section>
      <section className="pr-insight-section"><div className="pr-report-list-head"><div><p className="pr-eyebrow">RECENT AI FLAGS</p><h2>Evidence review leads</h2></div><span>{flags.length} available</span></div>
        <div className="pr-insight-list">{flags.length === 0 ? <Empty message="No AI flags are available yet." /> : flags.slice(0, 8).map(({ flag, evidence, caseItem }) => <article className="pr-insight-row pr-flag-row" key={flag.id}><div className="pr-insight-row-copy"><div className="pr-insight-row-top"><strong>{titleCase(flag.threat_class)}</strong><span className={`status-chip status-${flag.review_status}`}>{titleCase(flag.review_status)}</span></div><p>{flag.snippet}</p><small>{caseItem.case_ref} · {evidence.filename} · {formatDate(evidence.uploaded_at)}</small><small>Severity: {titleCase(flag.severity)} · System score: {Math.round(flag.confidence * 100)}%</small></div><Link className="pr-report-link" href={`/evidence/${evidence.id}`}>Review evidence <span aria-hidden="true">→</span></Link></article>)}</div>
      </section>
      <footer className="pr-report-note">AI flags and shared identifiers are review leads, not findings of guilt or proof of authenticity. Check the original evidence and context before recording a decision.</footer>
    </>}
  </main>;
}

function Metric({ label, value }: { label: string; value: number }) { return <article><span>{label}</span><strong>{value}</strong><small>Across available cases</small></article>; }
function Empty({ message }: { message: string }) { return <div className="pr-reports-state">{message}</div>; }
