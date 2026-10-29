"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { ApiError, deleteExternalComplaintReference, downloadComplaintPacket, getComplaintPreview, getExternalComplaintReference, saveExternalComplaintReference } from "@/lib/api";
import { formatDate, titleCase } from "@/lib/format";
import { useSessionUser } from "@/lib/session";
import type { ComplaintAiNoteFeedback, ComplaintChannel, ComplaintPacketInput, ComplaintPreview, ExternalComplaintReference } from "@/lib/types";

type ComplaintFields = Omit<ComplaintPacketInput, "reviewed_evidence_and_notes" | "understands_not_submitted">;

const blankFields: ComplaintFields = {
  channel: "cybercrime_portal",
  incident_date: "",
  incident_time: "",
  timezone_note: "",
  platform: "",
  account_or_handle: "",
  profile_url: "",
  state: "",
  district: "",
  police_station: "",
  statement: "",
};

export default function ComplaintPreparationPage() {
  const params = useParams<{ id: string }>();
  const caseId = decodeURIComponent(params.id);
  const user = useSessionUser();
  const [preview, setPreview] = useState<ComplaintPreview | null>(null);
  const [fields, setFields] = useState<ComplaintFields>(blankFields);
  const [reviewed, setReviewed] = useState(false);
  const [notSubmitted, setNotSubmitted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [generatedChannel, setGeneratedChannel] = useState<ComplaintChannel | null>(null);
  const [aiNoteFeedback, setAiNoteFeedback] = useState<Record<string, ComplaintAiNoteFeedback>>({});
  const [externalReference, setExternalReference] = useState<ExternalComplaintReference>({ saved: false, channel: null, last_four: null, updated_at: null });
  const [externalReferenceValue, setExternalReferenceValue] = useState("");
  const [externalReferenceChannel, setExternalReferenceChannel] = useState<ComplaintChannel>("cybercrime_portal");
  const [revealedExternalReference, setRevealedExternalReference] = useState("");
  const [externalReferenceBusy, setExternalReferenceBusy] = useState(false);
  const [externalReferenceMessage, setExternalReferenceMessage] = useState("");
  const [externalReferenceError, setExternalReferenceError] = useState("");

  useEffect(() => {
    if (user?.role !== "reporter") return;
    let active = true;
    getComplaintPreview(caseId)
      .then((data) => {
        if (!active) return;
        setPreview(data);
        setAiNoteFeedback(Object.fromEntries(data.ai_notes.map((note) => [note.flag_id, { flag_id: note.flag_id, include: true, reporter_comment: "" }])));
        setFields((current) => current.incident_date ? current : {
          ...current,
          incident_date: data.incident_date_on_record?.slice(0, 10) || "",
        });
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof ApiError ? reason.message : "Could not load this case for complaint preparation.");
      })
      .finally(() => { if (active) setLoading(false); });
    getExternalComplaintReference(caseId)
      .then((reference) => {
        if (!active) return;
        setExternalReference(reference);
        if (reference.channel) setExternalReferenceChannel(reference.channel);
      })
      .catch(() => {
        if (active) setExternalReferenceError("The saved reference could not be loaded. You can still prepare your complaint draft.");
      });
    return () => { active = false; };
  }, [caseId, user?.role]);

  function update<K extends keyof ComplaintFields>(key: K, value: ComplaintFields[K]) {
    setFields((current) => ({ ...current, [key]: value }));
    setSuccess("");
  }

  function updateChannel(channel: ComplaintChannel) {
    setFields((current) => ({
      ...current,
      channel,
      ...(channel === "cybercrime_portal" ? { state: "", district: "", police_station: "" } : {}),
    }));
    setSuccess("");
  }

  function updateAiNote(flagId: string, update: Partial<ComplaintAiNoteFeedback>) {
    setAiNoteFeedback((current) => ({
      ...current,
      [flagId]: { ...{ flag_id: flagId, include: true, reporter_comment: "" }, ...current[flagId], ...update },
    }));
  }

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!preview || !reviewed || !notSubmitted) return;
    setGenerating(true);
    setError("");
    setSuccess("");
    try {
      const packet = await downloadComplaintPacket(preview.case_id, preview.case_ref, {
        ...fields,
        reviewed_evidence_and_notes: true,
        understands_not_submitted: true,
        ai_note_feedback: preview.ai_notes.map((note) => aiNoteFeedback[note.flag_id] || { flag_id: note.flag_id, include: true }),
      });
      setGeneratedChannel(fields.channel);
      const formatNote = packet.format === "utf-8-text" ? " A UTF-8 text file preserves the language in your statement; open and review it before using it on the official form." : "";
      setSuccess(`Draft downloaded. Nothing was sent.${formatNote}${packet.digest ? ` Packet SHA-256: ${packet.digest}` : ""}`);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "The complaint draft could not be generated.");
    } finally {
      setGenerating(false);
    }
  }

  async function saveExternalReference() {
    if (externalReferenceValue.trim().length < 3) {
      setExternalReferenceError("Enter at least 3 characters, or leave this optional field empty.");
      return;
    }
    setExternalReferenceBusy(true);
    setExternalReferenceError("");
    setExternalReferenceMessage("");
    try {
      const saved = await saveExternalComplaintReference(caseId, {
        channel: externalReferenceChannel,
        reference: externalReferenceValue.trim(),
      });
      setExternalReference(saved);
      setRevealedExternalReference("");
      setExternalReferenceValue("");
      setExternalReferenceMessage("Saved encrypted. You can remove it whenever you choose.");
    } catch (reason) {
      setExternalReferenceError(reason instanceof ApiError ? reason.message : "The reference could not be saved.");
    } finally {
      setExternalReferenceBusy(false);
    }
  }

  async function removeExternalReference() {
    setExternalReferenceBusy(true);
    setExternalReferenceError("");
    setExternalReferenceMessage("");
    try {
      setExternalReference(await deleteExternalComplaintReference(caseId));
      setRevealedExternalReference("");
      setExternalReferenceMessage("The saved reference was removed.");
    } catch (reason) {
      setExternalReferenceError(reason instanceof ApiError ? reason.message : "The reference could not be removed.");
    } finally {
      setExternalReferenceBusy(false);
    }
  }

  async function revealExternalReference() {
    if (revealedExternalReference) {
      setRevealedExternalReference("");
      return;
    }
    setExternalReferenceBusy(true);
    setExternalReferenceError("");
    try {
      const revealed = await getExternalComplaintReference(caseId, true);
      setRevealedExternalReference(revealed.reference || "");
      if (!revealed.reference) setExternalReferenceError("The reference is no longer available.");
    } catch (reason) {
      setExternalReferenceError(reason instanceof ApiError ? reason.message : "The reference could not be revealed.");
    } finally {
      setExternalReferenceBusy(false);
    }
  }

  if (user?.role && user.role !== "reporter") return <div className="page-heading"><Link className="back-link" href={`/cases/${caseId}`}>← Back to case</Link><div className="inline-error" role="alert"><strong>Reporter access only</strong><span>Only the reporter who owns this case can prepare its complaint packet.</span></div></div>;
  if (!user) return <div className="page-heading"><div className="inline-error" role="status"><strong>Sign in as the reporter</strong><span>This preparation flow is available to the reporter who owns the case.</span></div></div>;
  if (loading) return <div className="table-state"><div className="spinner" /><span>Loading case evidence…</span></div>;

  return <>
    <div className="detail-back"><Link className="back-link" href={`/cases/${caseId}`}>← Back to case</Link></div>
    <div className="page-heading">
      <div className="eyebrow">REPORTER CONTROLLED <span>·</span> {preview?.case_ref || "CASE"}</div>
      <h1>Prepare a complaint draft</h1>
      <p>Review your case, add only the details that help explain what happened, then download a draft to submit yourself.</p>
    </div>

    <div className="complaint-alert" role="note">
      <strong>Nothing is submitted from DigitalWitness.</strong>
      <span>This is a preparation tool. The PDF is a draft, not an FIR or an official finding. Your statement is used to generate the download and is not saved in the database or audit trail.</span>
    </div>
    {error && <div className="form-error" role="alert">{error}</div>}
    {!preview ? <section className="panel complaint-panel"><h2>Case could not be prepared</h2><p>{error || "This case is unavailable or is not owned by this reporter account."}</p></section> : <form className="complaint-layout" onSubmit={generate}>
      <div className="complaint-main">
        <section className="panel complaint-panel" aria-labelledby="complaint-details-heading">
          <div className="panel-title-row"><div><span className="eyebrow">01 · YOUR DETAILS</span><h2 id="complaint-details-heading">What would you like to report?</h2><p>Fields marked optional can be left blank if you are unsure.</p></div></div>

          <fieldset className="complaint-channel">
            <legend>Where do you plan to report?</legend>
            <label className={`choice-card ${fields.channel === "cybercrime_portal" ? "choice-active" : ""}`}>
              <input type="radio" name="channel" value="cybercrime_portal" checked={fields.channel === "cybercrime_portal"} onChange={() => updateChannel("cybercrime_portal")} />
              <span><strong>National Cyber Crime Reporting Portal</strong><small>Opens the official portal after you download your draft.</small></span>
            </label>
            <label className={`choice-card ${fields.channel === "local_police" ? "choice-active" : ""}`}>
              <input type="radio" name="channel" value="local_police" checked={fields.channel === "local_police"} onChange={() => updateChannel("local_police")} />
              <span><strong>Local police</strong><small>Take the downloaded draft and original evidence to a police station.</small></span>
            </label>
          </fieldset>
          <p className="complaint-hint">An official portal may ask for identity or contact details depending on the reporting route. DigitalWitness does not collect those details here; provide them only on the official channel if you choose to continue.</p>

          <div className="complaint-fields">
            <label>Incident date <span className="optional">Optional</span><input type="date" value={fields.incident_date || ""} onChange={(event) => update("incident_date", event.target.value)} />{preview.incident_date_on_record && <small className="complaint-prefill-note">Prefilled from this case. Edit if the date is not accurate.</small>}</label>
            <label>Approximate time <span className="optional">Optional</span><input type="time" value={fields.incident_time || ""} onChange={(event) => update("incident_time", event.target.value)} /></label>
            <label>Timezone note <span className="optional">Optional</span><input maxLength={80} placeholder="e.g. India Standard Time" value={fields.timezone_note || ""} onChange={(event) => update("timezone_note", event.target.value)} /></label>
            <label>Platform or service <span className="required-label">Required</span><input required maxLength={120} placeholder="e.g. Instagram, WhatsApp" value={fields.platform} onChange={(event) => update("platform", event.target.value)} /></label>
            <label>Account name or handle <span className="optional">Optional</span><input maxLength={200} placeholder="If known" value={fields.account_or_handle || ""} onChange={(event) => update("account_or_handle", event.target.value)} /></label>
            <label>Profile or content link <span className="optional">Optional</span><input type="url" maxLength={500} placeholder="https://…" value={fields.profile_url || ""} onChange={(event) => update("profile_url", event.target.value)} /></label>
            {fields.channel === "local_police" && <><label>State / UT <span className="optional">Optional</span><input maxLength={100} value={fields.state || ""} onChange={(event) => update("state", event.target.value)} /></label><label>District <span className="optional">Optional</span><input maxLength={100} value={fields.district || ""} onChange={(event) => update("district", event.target.value)} /></label><label>Local police station <span className="optional">Optional</span><input maxLength={160} value={fields.police_station || ""} onChange={(event) => update("police_station", event.target.value)} /><small>Only add these details if you want them in your draft. DigitalWitness will not search for or select a station.</small></label></>}
            <label className="complaint-statement">Your statement <span className="required-label">Required</span><textarea required minLength={20} maxLength={6000} rows={8} placeholder="Describe what happened in your own words. Include relevant dates, messages, or actions. Do not include Aadhaar numbers, passwords, full home address, or unrelated private details." value={fields.statement} onChange={(event) => update("statement", event.target.value)} /><small>{fields.statement.length}/6000 characters · This text is included in the PDF, not saved by DigitalWitness.</small></label>
          </div>
        </section>

        <section className="panel complaint-panel" aria-labelledby="complaint-review-heading">
          <div className="panel-title-row"><div><span className="eyebrow">02 · REVIEW BEFORE DOWNLOAD</span><h2 id="complaint-review-heading">Check the case material</h2><p>Only records from this case are included. Open each original file and check its contents before continuing.</p></div><span className="count-pill">{preview.evidence.length} evidence file{preview.evidence.length === 1 ? "" : "s"}</span></div>
          {preview.evidence.length ? <div className="complaint-evidence-list">{preview.evidence.map((evidence) => <article className="complaint-evidence-card" key={evidence.evidence_id}>
            <div><Link href={`/evidence/${evidence.evidence_id}`}><strong>{evidence.filename}</strong><span>Open original ↗</span></Link><small>Uploaded {formatDate(evidence.uploaded_at)} · Analysis {titleCase(evidence.analysis_status)}</small></div>
            <code title={evidence.sha256}>SHA-256 {evidence.sha256}</code>
            <span className="complaint-status">Integrity: {titleCase(evidence.verification)} · Anchor: {titleCase(evidence.anchor_status)}</span>
          </article>)}</div> : <div className="activity-empty">No evidence is attached yet. You can still prepare a written draft, but there will be no evidence manifest.</div>}
          {preview.ai_notes.length ? <div className="complaint-notes"><h3>AI-assisted notes · {preview.ai_notes.length}</h3><p>These are review leads, not findings. A “confirmed” label only records a human review of the suggestion; it does not confirm an offence. You can leave a correction for this draft or leave a suggestion out; this does not change the saved AI note.</p>{preview.ai_notes.map((note) => {
            const feedback = aiNoteFeedback[note.flag_id] || { flag_id: note.flag_id, include: true, reporter_comment: "" };
            return <article className="complaint-note-card" key={note.flag_id}>
            <div><span className={`review-status review-${note.review_status}`}>{titleCase(note.review_status)}</span><strong>{titleCase(note.category)} · {titleCase(note.severity)}</strong></div>
            <small>Source: {note.filename}</small><blockquote>{note.snippet}</blockquote>
            <label className="complaint-check"><input type="checkbox" checked={feedback.include} onChange={(event) => updateAiNote(note.flag_id, { include: event.target.checked })} /><span>Include this suggestion in my complaint draft</span></label>
            <label className="ai-note-correction">My correction or context <span className="optional">Optional</span><textarea rows={2} maxLength={1000} disabled={!feedback.include} value={feedback.reporter_comment || ""} onChange={(event) => updateAiNote(note.flag_id, { reporter_comment: event.target.value })} placeholder="For example, explain why this excerpt is missing context." /><small>Included only in this download and labeled as your own note, not independently verified.</small></label>
          </article>;
          })}</div> : <div className="activity-empty">No AI notes are recorded for this case.</div>}
          {preview.analysis_pending_count > 0 && <p className="complaint-hint">{preview.analysis_pending_count} file(s) still have analysis pending. You can wait for them or prepare a draft now; this packet will show only available notes.</p>}
          {preview.analysis_unavailable_count > 0 && <p className="complaint-hint">Analysis was unavailable for {preview.analysis_unavailable_count} file(s). The original file remains in the evidence manifest.</p>}
          <ul className="case-summary-limitations">{preview.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
        </section>

        <section className="panel complaint-panel" aria-labelledby="complaint-confirm-heading">
          <div className="panel-title-row"><div><span className="eyebrow">03 · YOUR CHOICE</span><h2 id="complaint-confirm-heading">Confirm and prepare the draft</h2><p>Generating a draft does not contact the police or the reporting portal.</p></div></div>
          <label className="complaint-check"><input type="checkbox" checked={reviewed} onChange={(event) => setReviewed(event.target.checked)} /><span>I reviewed the evidence list and AI-assisted notes above, including their limitations.</span></label>
          <label className="complaint-check"><input type="checkbox" checked={notSubmitted} onChange={(event) => setNotSubmitted(event.target.checked)} /><span>I understand this is a draft and DigitalWitness will not file or send it for me.</span></label>
          <button className="button button-primary complaint-submit" type="submit" disabled={generating || !reviewed || !notSubmitted || !fields.platform.trim() || fields.statement.trim().length < 20}>{generating ? "Preparing your draft…" : "Download complaint draft"}<span>↓</span></button>
          {success && <div className="inline-success" role="status">{success}</div>}
          {generatedChannel === "cybercrime_portal" && success && <div className="complaint-handoff"><strong>Your next step is yours</strong><p>Review the downloaded file and original evidence. If you choose, open the official National Cyber Crime Reporting Portal and submit there yourself.</p><a className="button button-subtle" href="https://www.cybercrime.gov.in/" target="_blank" rel="noopener noreferrer">Open official reporting portal ↗</a><small>The portal may require sign-in, identity, or other details depending on the reporting route. This app does not send the packet there.</small></div>}
          {generatedChannel === "local_police" && success && <div className="complaint-handoff"><strong>Take the packet to local police</strong><p>Bring the downloaded draft and original evidence. Call or visit the appropriate official service yourself; DigitalWitness does not choose or contact a station.</p></div>}
          {(generatedChannel || externalReference.saved) && <details className="external-reference-panel" open={externalReference.saved}>
            <summary>Already reported outside DigitalWitness? Save the reference (optional)</summary>
            <p>Only add a reference if you choose to. It is encrypted in storage, available only from your reporter account, and never added to the blockchain or the complaint packet. The audit log records only that you saved or removed one.</p>
            {externalReference.saved && <div className="external-reference-saved"><span>Saved for {externalReference.channel === "local_police" ? "local police" : "the National Cyber Crime Reporting Portal"} · ending in <strong>{externalReference.last_four}</strong></span><div><button className="text-button" type="button" onClick={revealExternalReference} disabled={externalReferenceBusy}>{revealedExternalReference ? "Hide reference" : externalReferenceBusy ? "Loading…" : "Reveal reference"}</button><button className="text-button" type="button" onClick={removeExternalReference} disabled={externalReferenceBusy}>Remove</button></div>{revealedExternalReference && <code className="revealed-external-reference">{revealedExternalReference}</code>}</div>}
            <div className="external-reference-fields">
              <label>Reporting channel<select value={externalReferenceChannel} onChange={(event) => setExternalReferenceChannel(event.target.value as ComplaintChannel)}><option value="cybercrime_portal">National Cyber Crime Reporting Portal</option><option value="local_police">Local police</option></select></label>
              <label>Reference number<input autoComplete="off" maxLength={160} value={externalReferenceValue} onChange={(event) => setExternalReferenceValue(event.target.value)} placeholder="Optional — enter only after you receive one" /></label>
            </div>
            <button className="button button-subtle" type="button" onClick={saveExternalReference} disabled={externalReferenceBusy || externalReferenceValue.trim().length < 3}>{externalReferenceBusy ? "Saving…" : externalReference.saved ? "Replace saved reference" : "Save reference privately"}</button>
            {externalReferenceMessage && <p className="inline-success" role="status">{externalReferenceMessage}</p>}
            {externalReferenceError && <p className="form-error" role="alert">{externalReferenceError}</p>}
          </details>}
        </section>
      </div>
      <aside className="complaint-aside">
        <div className="aside-card aside-highlight"><div className="aside-icon">✓</div><strong>Private by design</strong><p>No Aadhaar, passwords, or full home address are requested. The statement is only used to create this download.</p></div>
        <div className="aside-card"><strong>What this packet includes</strong><ul><li>Your statement and selected reporting channel</li><li>Evidence filenames and SHA-256 fingerprints</li><li>Case-specific AI notes, clearly labeled as suggestions</li></ul></div>
        <div className="aside-card"><strong>What it does not do</strong><ul><li>Submit a complaint or create an FIR</li><li>Prove a screenshot or video is authentic</li><li>Make a legal finding or predict guilt</li></ul></div>
      </aside>
    </form>}
  </>;
}
