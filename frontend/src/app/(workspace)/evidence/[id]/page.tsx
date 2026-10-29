"use client";

import Link from "next/link";
import Image from "next/image";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, getAnalysis, getCase, getEvidence, getEvidenceFile, verifyEvidence } from "@/lib/api";
import { formatBytes, formatDate, shortHash, titleCase } from "@/lib/format";
import type { Analysis, CaseDetail, EvidenceSummary, Verification } from "@/lib/types";
import { VerifyBadge } from "@/components/verify-badge";

function getInvestigationSummary(analysis: Analysis): string {
  if (analysis.status === "pending" || analysis.status === "running") {
    return "Automated review is still processing this file. This page will refresh the analysis status while it runs.";
  }
  if (analysis.status === "failed") {
    return "Automated review did not complete. An investigator can retry it from the case review queue.";
  }
  if (analysis.status === "skipped") {
    return "No usable text was extracted. Review the original image or video directly; a skipped result is not an authenticity verdict.";
  }
  if (analysis.status !== "done") {
    return "No completed review is available yet. Check the analysis status and review the original evidence.";
  }
  if (analysis.flags.length === 0 && analysis.entities.length === 0) {
    return "The automated review returned no potential threat flags or contact/account indicators. This does not establish that the evidence is authentic, harmless, or complete.";
  }

  const highestSeverity = ["critical", "high", "medium", "low"].find((severity) =>
    analysis.flags.some((flag) => flag.severity === severity)
  );
  const severityNote = highestSeverity ? ` Highest suggested severity: ${titleCase(highestSeverity)}.` : "";
  return `The automated review returned ${analysis.flags.length} potential flag${analysis.flags.length === 1 ? "" : "s"} and ${analysis.entities.length} possible contact or account indicator${analysis.entities.length === 1 ? "" : "s"}.${severityNote} A human reviewer must verify each item against the source evidence; these are leads, not findings.`;
}

function analysisMethod(analysis: Analysis): string {
  if (analysis.analysis_source === "llm+rules") return "AI model with local rules";
  if (analysis.analysis_source?.startsWith("rules-")) return "Local rules only";
  return analysis.model || analysis.extraction_method || "Method not recorded";
}

export default function EvidencePage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id);
  const [item, setItem] = useState<EvidenceSummary | null>(null);
  const [parent, setParent] = useState<CaseDetail | null>(null);
  const [preview, setPreview] = useState("");
  const [textPreview, setTextPreview] = useState("");
  const [previewError, setPreviewError] = useState("");
  const [verification, setVerification] = useState<Verification | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [analysisError, setAnalysisError] = useState("");
  const [error, setError] = useState("");
  const [checking, setChecking] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    let objectUrl = "";
    async function load() {
      try {
        const evidence = await getEvidence(id);
        if (!alive) return;
        setItem(evidence);
        const [caseResult, fileResult, analysisResult] = await Promise.allSettled([getCase(evidence.case_id), getEvidenceFile(id), getAnalysis(id)]);
        if (!alive) return;
        if (caseResult.status === "fulfilled") setParent(caseResult.value);
        if (analysisResult.status === "fulfilled") setAnalysis(analysisResult.value);
        else if (analysisResult.reason instanceof ApiError && analysisResult.reason.status === 403) setAnalysisError("Analysis details are limited to investigator, legal, or admin accounts. Sign in with an authorized review account to view them.");
        else if (analysisResult.reason instanceof ApiError && analysisResult.reason.status === 401) setAnalysisError("Your session expired. Sign in again to view analysis details.");
        else setAnalysisError("Analysis details could not be loaded. Check that the analysis worker has processed this upload.");
        if (fileResult.status === "fulfilled") {
          const blob = fileResult.value;
          if (evidence.mime_type === "text/plain" || evidence.mime_type === "application/json") setTextPreview(await blob.text());
          else { objectUrl = URL.createObjectURL(blob); setPreview(objectUrl); }
        } else setPreviewError(fileResult.reason instanceof ApiError ? fileResult.reason.message : "The file preview could not be loaded.");
      } catch (reason) { if (alive) setError(reason instanceof ApiError ? reason.message : "Could not load evidence details."); }
      finally { if (alive) setLoading(false); }
    }
    load();
    return () => { alive = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [id]);

  useEffect(() => {
    if (!analysis || !["pending", "running"].includes(analysis.status)) return;
    let alive = true;
    let refreshing = false;
    const timer = window.setInterval(async () => {
      if (refreshing) return;
      refreshing = true;
      try {
        const latest = await getAnalysis(id);
        if (alive) setAnalysis(latest);
      } catch {
        // Keep the current status visible and retry on the next interval.
      } finally {
        refreshing = false;
      }
    }, 5000);
    return () => { alive = false; window.clearInterval(timer); };
  }, [analysis, id]);

  async function verify() {
    setChecking(true); setError("");
    try { setVerification(await verifyEvidence(id)); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : "The integrity check could not be completed."); }
    finally { setChecking(false); }
  }

  if (loading) return <div className="table-state"><div className="spinner" /><span>Loading evidence…</span></div>;
  if (error && !item) return <div className="inline-error" role="alert"><strong>Evidence is unavailable</strong><span>{error}</span><Link className="button button-subtle" href="/cases">Back to cases</Link></div>;
  if (!item) return null;
  const result = verification?.result || item.verification;
  const mime = item.mime_type.toLowerCase();
  const summary = analysis ? getInvestigationSummary(analysis) : "Investigator-only analysis is not available for this account.";
  const analysisMethodLabel = analysis ? analysisMethod(analysis) : "Not available";
  const previewContent = mime.startsWith("image/") ? <Image className="evidence-image-preview" src={preview} alt={`Preview of ${item.filename}`} width={1200} height={900} unoptimized />
    : mime === "application/pdf" ? <iframe className="evidence-pdf-preview" src={preview} title={`PDF preview of ${item.filename}`} />
    : mime.startsWith("audio/") ? <audio controls src={preview}>Audio preview is not supported in this browser.</audio>
    : mime.startsWith("video/") ? <video controls className="evidence-video-preview" src={preview}>Video preview is not supported in this browser.</video>
    : mime === "text/plain" || mime === "application/json" ? <pre className="plain-preview">{textPreview || "No text preview is available."}</pre>
    : preview ? <a className="button button-subtle" href={preview} download={item.filename}>Download preview file</a>
    : <div className="preview-placeholder"><span>▤</span><strong>File preview is not available</strong><small>{previewError || "Metadata and integrity information remain available below."}</small></div>;

  return <>
    <div className="detail-back"><Link className="back-link" href={parent ? `/cases/${parent.id}` : "/cases"}>← {parent?.case_ref || "Case workspace"}</Link></div>
    <div className="page-heading evidence-heading"><div><div className="eyebrow">EVIDENCE VIEWER <span>·</span> {item.id.slice(0, 12)}</div><h1>{item.filename}</h1><p>Submitted {formatDate(item.uploaded_at)} <span>·</span> {formatBytes(item.size_bytes)}</p></div><div className="heading-actions"><button className="button button-primary" onClick={verify} disabled={checking}>{checking ? "Checking…" : "Run integrity check"}<span>↻</span></button></div></div>
    {error && <div className="form-error" role="alert">{error}</div>}
    <div className="evidence-view-layout"><section className="panel preview-panel"><div className="preview-top"><span className="eyebrow">FILE PREVIEW</span><span className="preview-type">{item.mime_type}</span></div><div className="preview-canvas">{previewContent}</div></section>
      <aside className="evidence-side"><section className="panel integrity-card"><div className="panel-title-row"><div><span className="eyebrow">INTEGRITY STATUS</span><h2>{result === "verified" ? "File check complete" : result === "altered" ? "Hash does not match" : result === "pending" ? "Waiting for anchor" : result === "not_checked" ? "Ready for integrity check" : "Check unavailable"}</h2></div></div><VerifyBadge result={result} />{verification && <p className="verification-message">{verification.message}</p>}<div className="integrity-hash"><span>Recorded SHA-256</span><code>{item.sha256}</code><button className="text-button" onClick={() => navigator.clipboard.writeText(item.sha256)}>Copy hash</button></div></section>
      <section className="panel metadata-card"><div className="panel-title-row"><div><span className="eyebrow">ANCHOR DETAILS</span><h2>Chain record</h2></div></div><dl className="metadata-list"><div><dt>Evidence status</dt><dd><span className={`status-chip status-${item.status}`}>{titleCase(item.status)}</span></dd></div><div><dt>Batch</dt><dd>{item.batch_id ? shortHash(item.batch_id, 8) : "Not anchored yet"}</dd></div><div><dt>Batch root</dt><dd><code>{shortHash(item.batch_root, 8)}</code></dd></div><div><dt>Transaction</dt><dd>{item.tx_hash ? item.explorer_url ? <a className="external-link" href={item.explorer_url} target="_blank" rel="noreferrer">{shortHash(item.tx_hash, 8)} ↗</a> : <code>{shortHash(item.tx_hash, 8)}</code> : "Not available"}</dd></div><div><dt>File size</dt><dd>{formatBytes(item.size_bytes)}</dd></div><div><dt>Uploaded</dt><dd title={new Date(item.uploaded_at).toISOString()}>{formatDate(item.uploaded_at)}</dd></div></dl></section>
      <section className="panel metadata-card"><div className="panel-title-row"><div><span className="eyebrow">INVESTIGATION SUPPORT</span><h2>Analysis details</h2></div></div>{analysisError && <p className="verification-message" role="status">{analysisError}</p>}<dl className="metadata-list"><div><dt>Analysis status</dt><dd>{analysis?.status || (analysisError ? "Restricted or unavailable" : "Loading")}</dd></div><div><dt>Text extraction</dt><dd>{analysis?.extraction_method || (analysis?.status === "pending" || analysis?.status === "running" ? "Processing" : "Not available")}</dd></div><div><dt>Selected focus</dt><dd>{analysis?.investigation_categories?.length ? analysis.investigation_categories.map((value) => value.split("_").join(" ")).join(", ") : analysisError ? "Restricted or unavailable" : "No focus selected"}</dd></div>{analysis?.provenance && <><div><dt>File details</dt><dd>{[analysis.provenance.file_format, analysis.provenance.dimensions ? `${analysis.provenance.dimensions.width} × ${analysis.provenance.dimensions.height} px` : null, analysis.provenance.page_count !== undefined ? `${analysis.provenance.page_count} pages` : null].filter(Boolean).join(" · ") || "Not available"}</dd></div><div><dt>Metadata fields</dt><dd>{analysis.provenance.metadata_present ? "Some metadata fields are present." : "No listed metadata fields were observed."}</dd></div><div><dt>Metadata observations</dt><dd>{analysis.provenance.observations?.length ? analysis.provenance.observations.join(" ") : "No specific creator, date, or location fields were observed."}</dd></div></>}{analysis?.video && <div><dt>Video sampling</dt><dd>{analysis.video.frames_examined ?? 0}/{analysis.video.frames_examined_limit ?? 4} frames examined from {analysis.video.duration_seconds ?? "unknown"} seconds{analysis.video.sampled_timestamps_seconds?.length ? `; sampled near ${analysis.video.sampled_timestamps_seconds.map((time) => `${time}s`).join(", ")}` : ""}.</dd></div>}</dl><p className="verification-message">Metadata can be absent or spoofed. Automated analysis provides review leads only; it cannot establish whether media is authentic or whether a crime occurred.</p></section></aside>
    </div>
    {analysis?.coverage && <section className="panel coverage-card"><div className="panel-title-row"><div><span className="eyebrow">ANALYSIS COVERAGE</span><h2>What the system examined</h2></div><span className={`status-chip status-${analysis.coverage.status}`}>{titleCase(analysis.coverage.status)}</span></div><p>{analysis.coverage.characters_extracted.toLocaleString()} extracted characters{analysis.coverage.units_examined !== null && analysis.coverage.units_examined !== undefined ? ` · ${analysis.coverage.units_examined}${analysis.coverage.units_total !== null && analysis.coverage.units_total !== undefined ? ` of ${analysis.coverage.units_total}` : ""} unit(s) examined` : ""}{analysis.coverage.truncated ? " · text reached the processing limit" : ""}</p>{analysis.coverage.notes.length > 0 && <ul className="observation-list">{analysis.coverage.notes.map((note) => <li key={note}>{note}</li>)}</ul>}</section>}
    <section className="panel investigation-output" aria-labelledby="investigation-output-heading">
      <div className="panel-title-row"><div><span className="eyebrow">INVESTIGATOR VIEW</span><h2 id="investigation-output-heading">Investigative summary</h2><p>Structured review leads from this evidence file.</p></div>{analysis && <span className={`status-chip status-${analysis.status}`}>{titleCase(analysis.status)}</span>}</div>
      {analysisError ? <div className="analysis-output-empty" role="status">{analysisError}</div> : analysis ? <>
        <div className="investigation-summary"><span className="summary-label">AUTOMATED OVERVIEW · HUMAN REVIEW REQUIRED</span><p>{summary}</p><div className="analysis-method">Method: {analysisMethodLabel}{analysis.model && analysis.analysis_source ? ` · ${analysis.model}` : ""}{analysis.prompt_version ? ` · prompt ${analysis.prompt_version}` : ""}</div></div>

        <div className="analysis-result-grid">
          <section className="analysis-result-section" aria-labelledby="observations-heading"><div className="analysis-section-heading"><div><h3 id="observations-heading">File observations</h3><p>Technical metadata only; values can be missing or altered.</p></div></div>
            {analysis.provenance?.observations?.length ? <ul className="observation-list">{analysis.provenance.observations.map((observation, index) => <li key={`${index}-${observation}`}>{observation}</li>)}</ul> : <p className="analysis-muted">No specific metadata observations were recorded.</p>}
            {analysis.provenance?.caveat && <p className="analysis-caveat">{analysis.provenance.caveat}</p>}
          </section>
          {analysis.video && <section className="analysis-result-section" aria-labelledby="video-analysis-heading"><div className="analysis-section-heading"><div><h3 id="video-analysis-heading">Video analysis</h3><p>Only a limited sample of frames was examined.</p></div></div>
            <dl className="video-detail-grid"><div><dt>Duration</dt><dd>{analysis.video.duration_seconds ?? "Unknown"} sec</dd></div><div><dt>Frames examined</dt><dd>{analysis.video.frames_examined ?? 0} of {analysis.video.frames_examined_limit ?? 4}</dd></div>{analysis.video.video_codec && <div><dt>Video format</dt><dd>{analysis.video.video_codec}</dd></div>}{analysis.video.frame_width && analysis.video.frame_height && <div><dt>Frame size</dt><dd>{analysis.video.frame_width} × {analysis.video.frame_height}</dd></div>}{analysis.video.frame_rate && <div><dt>Frame rate</dt><dd>{analysis.video.frame_rate} fps</dd></div>}</dl>
            {analysis.video.sampled_timestamps_seconds?.length ? <p className="analysis-muted">Sample points: {analysis.video.sampled_timestamps_seconds.map((time) => `${time}s`).join(" · ")}</p> : null}{analysis.video.caveat && <p className="analysis-caveat">{analysis.video.caveat}</p>}
          </section>}
        </div>

        <section className="analysis-result-section analysis-full-section" aria-labelledby="extracted-text-heading"><div className="analysis-section-heading"><div><h3 id="extracted-text-heading">OCR and extracted text</h3><p>{analysis.text ? `${analysis.text.length.toLocaleString()} characters extracted` : "No text was extracted from this file."}</p></div></div>
          {analysis.text ? <details className="extracted-text-details"><summary>Show extracted text</summary><pre className="extracted-text">{analysis.text}</pre></details> : <p className="analysis-muted">For image or video evidence, review the original media above. A lack of extracted text does not mean there is no relevant visual content.</p>}
        </section>

        <section className="analysis-result-section analysis-full-section" aria-labelledby="potential-flags-heading"><div className="analysis-section-heading"><div><h3 id="potential-flags-heading">Potential threat flags</h3><p>Model or rule suggestions; they must be checked against the source.</p></div><span className="count-pill">{analysis.flags.length} {analysis.flags.length === 1 ? "flag" : "flags"}</span></div>
          {analysis.flags.length ? <div className="analysis-flag-grid">{analysis.flags.map((flag) => <article className={`flag-card severity-${flag.severity}`} key={flag.id}><div className="flag-topline"><span className={`severity-tag severity-tag-${flag.severity}`}>{titleCase(flag.severity)}</span><span className={`review-status review-${flag.review_status}`}>{titleCase(flag.review_status)}</span></div><h4>{titleCase(flag.threat_class)}</h4><blockquote>{flag.snippet}</blockquote>{flag.reason && <p className="analysis-muted">{flag.reason}</p>}<small>{Math.round(flag.confidence * 100)}% uncalibrated triage score · not a probability of truth or guilt</small></article>)}</div> : <p className="analysis-muted">No potential flags were returned by the automated review.</p>}
        </section>

        <section className="analysis-result-section analysis-full-section" aria-labelledby="indicators-heading"><div className="analysis-section-heading"><div><h3 id="indicators-heading">Extracted contact and account indicators</h3><p>Possible handles, phone numbers, email addresses, or links in the extracted text.</p></div><span className="count-pill">{analysis.entities.length} {analysis.entities.length === 1 ? "indicator" : "indicators"}</span></div>
          {analysis.entities.length ? <div className="analysis-entity-list">{analysis.entities.map((entity) => <article className="analysis-entity" key={entity.id}><span>{titleCase(entity.type)}</span><strong>{entity.raw}</strong><small>{Math.round(entity.confidence * 100)}% uncalibrated extraction score</small></article>)}</div> : <p className="analysis-muted">No contact or account indicators were extracted.</p>}
        </section>
      </> : <div className="analysis-output-empty">{analysisError || "Analysis details are loading."}</div>}
      <p className="analysis-caveat analysis-caveat-final">This summary is generated from automated extraction and review leads. It does not determine authenticity, identify a person, predict criminality, or establish that an offence occurred.</p>
    </section>
    <div className="split-note"><div className="notice-icon">i</div><p><strong>Interpret the result carefully</strong><br />Verified means unchanged since anchoring. A passing check does not prove who created the file or whether the content is true.</p></div>
  </>;
}
