"use client";

import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, DragEvent, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, createCase, getCases, isMockMode, uploadEvidence, uploadLimitMb } from "@/lib/api";
import { formatBytes } from "@/lib/format";
import type { CaseSummary, Receipt } from "@/lib/types";
import { useSessionUser } from "@/lib/session";

const CATEGORIES: [string, string][] = [
  ["cyberstalking_bullying",    "Repeated contact or cyberstalking"],
  ["blackmail_threatening",     "Threats or blackmail"],
  ["intimate_image_abuse",      "Sharing intimate images without consent"],
  ["defamation_morphing",       "Defamation or altered images"],
  ["fake_profile_impersonation","Fake profile or impersonation"],
];

const STEP_LABELS = [
  "What happened",
  "Incident details",
  "Add evidence",
  "Review and save",
];

function StepHeader({ step, total }: { step: number; total: number }) {
  const pct = Math.round((step / total) * 100);
  return (
    <div className="wizard-step-header">
      <div className="step-progress-track">
        <div className="step-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="step-kicker">
        Step {step} of {total} · {STEP_LABELS[step - 1]}
      </span>
    </div>
  );
}

export function EvidenceUploader() {
  const role   = useSessionUser()?.role || "";
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const [step,                    setStep]                    = useState(1);
  const [existing,                setExisting]                = useState<CaseSummary[]>([]);
  const [caseMode,                setCaseMode]                = useState<"new" | string>("new");
  const [title,                   setTitle]                   = useState("");
  const [description,             setDescription]             = useState("");
  const [investigationCategories, setInvestigationCategories] = useState<string[]>([]);
  const [file,                    setFile]                    = useState<File | null>(null);
  const [dragging,                setDragging]                = useState(false);
  const [progress,                setProgress]                = useState(0);
  const [busy,                    setBusy]                    = useState(false);
  const [error,                   setError]                   = useState("");
  const [createdCase,             setCreatedCase]             = useState<CaseSummary | null>(null);

  useEffect(() => {
    getCases({ page_size: 100 })
      .then((r) => setExisting(r.items))
      .catch(() => setExisting([]));
  }, []);

  const maxBytes   = uploadLimitMb() * 1024 * 1024;
  const allowedExt = new Set(["jpg","jpeg","png","webp","pdf","txt","json","mp3","wav","m4a","mp4","mov","webm"]);

  function choose(next: File | null) {
    setError("");
    if (!next) { setFile(null); return; }
    if (next.size === 0) { setError("Empty files cannot be submitted."); return; }
    if (next.size > maxBytes) { setError(`Choose a file smaller than ${uploadLimitMb()} MB.`); return; }
    const ext = next.name.split(".").pop()?.toLowerCase() ?? "";
    if (!isMockMode() && !allowedExt.has(ext)) {
      setError("The connected API accepts JPG, PNG, WEBP, PDF, TXT, JSON, MP3, WAV, M4A, MP4, MOV and WEBM files.");
      return;
    }
    setFile(next);
  }

  function onFile(e: ChangeEvent<HTMLInputElement>) { choose(e.target.files?.[0] ?? null); }
  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault(); setDragging(false); choose(e.dataTransfer.files[0] ?? null);
  }

  function goBack() { setError(""); setStep((s) => Math.max(1, s - 1)); }

  function next1() { setError(""); setStep(2); }

  function next2() {
    setError("");
    if (caseMode === "new" && !title.trim()) {
      setError("Give this report a short title to continue."); return;
    }
    setStep(3);
  }

  function next3() {
    setError("");
    if (!file) { setError("Choose a file to continue."); return; }
    setStep(4);
  }

  async function submit(e: FormEvent) {
    e.preventDefault(); setError("");
    if (!file) { setError("Choose a file to continue."); return; }
    setBusy(true); setProgress(0); abortRef.current = new AbortController();
    try {
      const selected =
        caseMode === "new"
          ? await createCase({ title: title.trim(), description: description.trim() })
          : existing.find((c) => c.id === caseMode);
      if (!selected) throw new ApiError("The selected case is not available.");
      if (caseMode === "new") {
        setCreatedCase(selected);
        setExisting((cur) => [selected, ...cur]);
        setCaseMode(selected.id);
      }
      const receipt: Receipt = await uploadEvidence(
        selected, file, setProgress, abortRef.current.signal, investigationCategories,
      );
      router.push(`/receipts/${encodeURIComponent(receipt.receipt_id)}`);
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError")
        setError("Upload cancelled. The selected file was not submitted.");
      else
        setError(reason instanceof ApiError ? reason.message : "The report could not be submitted. Please try again.");
    } finally { setBusy(false); abortRef.current = null; }
  }

  if (role !== "reporter") {
    return (
      <div className="inline-error" role="alert">
        <strong>This workspace is for reporter submissions</strong>
        <span>Investigators review reports submitted by reporters. Open the investigation desk to review existing cases.</span>
        <Link className="button button-subtle" href="/cases">Open investigation desk</Link>
      </div>
    );
  }

  return (
    <div className="wizard-outer">
      <div className="wizard-container">

        {/* ── Step 1: What happened ─────────────────────────── */}
        {step === 1 && (
          <div className="wizard-step">
            <StepHeader step={1} total={4} />
            <h1 className="wizard-heading">What happened?</h1>
            <p className="wizard-sub">
              Tell us whether this is a new situation or one you&rsquo;ve already
              started documenting. You can add details in the next step.
            </p>

            {error && <div className="form-error" role="alert">{error}</div>}

            <fieldset className="case-choice wizard-choice">
              <legend className="sr-only">Where should this evidence go?</legend>

              <label className={`choice-card${caseMode === "new" ? " choice-active" : ""}`}>
                <input
                  type="radio" name="case-mode" value="new"
                  checked={caseMode === "new"}
                  onChange={() => setCaseMode("new")}
                />
                <span>
                  <strong>This is a new situation</strong>
                  <small>Start a new report and add your first file.</small>
                </span>
              </label>

              {existing.length > 0 && (
                <label className={`choice-card${caseMode !== "new" ? " choice-active" : ""}`}>
                  <input
                    type="radio" name="case-mode"
                    value={caseMode === "new" ? existing[0].id : caseMode}
                    checked={caseMode !== "new"}
                    onChange={() => setCaseMode(existing[0].id)}
                  />
                  <span>
                    <strong>I&rsquo;m adding to an existing report</strong>
                    <small>Choose one of your open cases.</small>
                  </span>
                </label>
              )}

              {caseMode !== "new" && existing.length > 0 && (
                <label className="case-select-label" style={{ marginTop: 4 }}>
                  Which report?
                  <select value={caseMode} onChange={(e) => setCaseMode(e.target.value)}>
                    {existing.map((c) => (
                      <option key={c.id} value={c.id}>{c.case_ref} — {c.title}</option>
                    ))}
                  </select>
                </label>
              )}
            </fieldset>

            <div className="wizard-actions">
              <button type="button" className="button button-primary wizard-next" onClick={next1}>
                Continue <span aria-hidden="true">→</span>
              </button>
            </div>

            <p className="wizard-privacy-note">
              <span aria-hidden="true">🔒</span>
              Your report is available to your reporter account and authorized review roles.
            </p>
          </div>
        )}

        {/* ── Step 2: Incident details ──────────────────────── */}
        {step === 2 && (
          <div className="wizard-step">
            <StepHeader step={2} total={4} />

            <button type="button" className="back-link wizard-back" onClick={goBack}>
              ← Back to what happened
            </button>

            <h1 className="wizard-heading">Describe the incident</h1>
            <p className="wizard-sub">
              Add a title and a short description. Keep it brief — you&rsquo;ll
              add evidence in the next step.
            </p>

            {error && <div className="form-error" role="alert">{error}</div>}

            {caseMode === "new" ? (
              <div className="form-stack wizard-fields">
                <label>
                  Give this report a short title
                  <input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    maxLength={255}
                    placeholder="For example: Repeated account impersonation"
                    autoFocus
                  />
                </label>

                <label>
                  Describe what happened{" "}
                  <span className="optional">· optional</span>
                  <textarea
                    rows={5}
                    maxLength={2000}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Write in your own words. It&apos;s fine to say you don&apos;t know the exact date or platform — add what you do know."
                  />
                </label>

                <fieldset className="case-choice" aria-describedby="focus-help">
                  <legend>
                    What should the review focus on?{" "}
                    <span className="optional">· optional</span>
                  </legend>
                  <small id="focus-help">
                    These choices guide review only. They do not determine whether
                    the evidence is true or harmful. Choose as many as apply, or none.
                  </small>
                  {CATEGORIES.map(([value, label]) => (
                    <label className="choice-card" key={value}>
                      <input
                        type="checkbox"
                        checked={investigationCategories.includes(value)}
                        onChange={(e) =>
                          setInvestigationCategories((cur) =>
                            e.target.checked
                              ? [...cur, value]
                              : cur.filter((i) => i !== value),
                          )
                        }
                      />
                      <span><strong>{label}</strong></span>
                    </label>
                  ))}
                  <label className="choice-card">
                    <input
                      type="checkbox"
                      checked={investigationCategories.length === 0}
                      onChange={() => setInvestigationCategories([])}
                    />
                    <span>
                      <strong>I don&rsquo;t know yet</strong>
                      <small>Skip this for now — you can update it later.</small>
                    </span>
                  </label>
                </fieldset>
              </div>
            ) : (
              <div className="wizard-existing-note">
                <p>You&rsquo;re adding to an existing report. Proceed directly to uploading your file.</p>
              </div>
            )}

            <div className="wizard-actions">
              <button type="button" className="button button-primary wizard-next" onClick={next2}>
                Save and continue <span aria-hidden="true">→</span>
              </button>
            </div>
          </div>
        )}

        {/* ── Step 3: Add evidence ──────────────────────────── */}
        {step === 3 && (
          <div className="wizard-step">
            <StepHeader step={3} total={4} />

            <button type="button" className="back-link wizard-back" onClick={goBack}>
              ← Back to incident details
            </button>

            <h1 className="wizard-heading">Add screenshots or documents</h1>
            <p className="wizard-sub">
              JPG, PNG, WEBP, PDF, TXT, JSON, MP3, WAV, M4A, MP4, MOV or WEBM ·
              video up to 60 s · {uploadLimitMb()} MB. One file at a time.
            </p>

            <div className="wizard-privacy-card">
              <span aria-hidden="true">🔒</span>
              <div>
                <strong>How your files are stored</strong>
                <span>
                  The service encrypts your file before storing it privately.
                  Only a batch fingerprint is recorded on the blockchain.
                  Access to the saved original is controlled by your account role.
                </span>
              </div>
            </div>

            {error && <div className="form-error" role="alert">{error}</div>}

            <input
              ref={inputRef}
              className="visually-hidden"
              type="file"
              accept=".jpg,.jpeg,.png,.webp,.pdf,.txt,.json,.mp3,.wav,.m4a,.mp4,.mov,.webm"
              onChange={onFile}
              aria-label="Select evidence file"
            />

            <div
              className={`dropzone wizard-dropzone${dragging ? " dropzone-active" : ""}${file ? " dropzone-file" : ""}`}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
            >
              {file ? (
                <>
                  <div className="file-icon">▤</div>
                  <div className="selected-file">
                    <strong>{file.name}</strong>
                    <span>{formatBytes(file.size)} · {file.type || "file"}</span>
                  </div>
                  <button type="button" className="text-button" onClick={() => choose(null)}>
                    Remove
                  </button>
                </>
              ) : (
                <>
                  <div className="upload-icon">↑</div>
                  <strong>Drop your file here</strong>
                  <span>
                    or{" "}
                    <button type="button" className="text-button" onClick={() => inputRef.current?.click()}>
                      browse files
                    </button>
                  </span>
                  <small>Your file&rsquo;s fingerprint is recorded before any processing.</small>
                </>
              )}
            </div>

            <div className="wizard-actions">
              <button type="button" className="button button-primary wizard-next" onClick={next3}>
                Save and continue <span aria-hidden="true">→</span>
              </button>
            </div>
          </div>
        )}

        {/* ── Step 4: Review and save ───────────────────────── */}
        {step === 4 && (
          <form className="wizard-step" onSubmit={submit}>
            <StepHeader step={4} total={4} />

            <button type="button" className="back-link wizard-back" onClick={goBack}>
              ← Back to add evidence
            </button>

            <h1 className="wizard-heading">Review and save</h1>
            <p className="wizard-sub">
              Check everything looks right before saving your report. Your file
              cannot be changed after this point.
            </p>

            {error && <div className="form-error" role="alert">{error}</div>}

            {createdCase && (
              <div className="inline-success">
                <strong>Report started.</strong> Your case is {createdCase.case_ref}.
                You can retry the file upload if needed.
              </div>
            )}

            {/* Summary */}
            <div className="wizard-review-card">
              <div className="wizard-review-row">
                <span className="wizard-review-label">Report</span>
                <span className="wizard-review-value">
                  {caseMode === "new"
                    ? title || <em className="wizard-empty">No title entered</em>
                    : existing.find((c) => c.id === caseMode)?.title ?? caseMode}
                </span>
              </div>
              {description.trim() && (
                <div className="wizard-review-row">
                  <span className="wizard-review-label">Description</span>
                  <span className="wizard-review-value wizard-review-desc">{description}</span>
                </div>
              )}
              {investigationCategories.length > 0 && (
                <div className="wizard-review-row">
                  <span className="wizard-review-label">Focus</span>
                  <span className="wizard-review-value">
                    {investigationCategories
                      .map((v) => CATEGORIES.find(([cat]) => cat === v)?.[1])
                      .filter(Boolean)
                      .join(", ")}
                  </span>
                </div>
              )}
              <div className="wizard-review-row">
                <span className="wizard-review-label">File</span>
                <span className="wizard-review-value">
                  {file
                    ? <><strong>{file.name}</strong> <em style={{ color: "#72818A", fontStyle: "normal" }}>{formatBytes(file.size)}</em></>
                    : <em className="wizard-empty">No file selected</em>}
                </span>
              </div>
            </div>

            {busy && (
              <div className="progress-area">
                <div className="progress-label">
                  <span>Saving securely…</span>
                  <strong>{progress}%</strong>
                </div>
                <div className="progress-track">
                  <div style={{ width: `${progress}%` }} />
                </div>
                <button className="text-button cancel-upload" type="button" onClick={() => abortRef.current?.abort()}>
                  Cancel upload
                </button>
              </div>
            )}

            <div className="wizard-submit-area">
              <span className="autosave-note">
                Your file cannot be changed after saving.
              </span>
              <button className="button button-primary wizard-next" disabled={busy} type="submit">
                {busy ? "Saving…" : "Save report"}{" "}
                <span aria-hidden="true">→</span>
              </button>
            </div>

            <p className="report-disclaimer">
              A fingerprint check can show whether a file changed after saving.
              It does not establish who created the file or whether its contents are accurate.
            </p>
          </form>
        )}

      </div>
    </div>
  );
}
