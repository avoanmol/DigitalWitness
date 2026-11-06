
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  createCase,
  listCases,
  uploadEvidence,
  USE_MOCK,
} from "@/lib/api";
import { useUser } from "@/lib/auth";
import { emptyFilters } from "@/components/FilterBar";
import type { CaseSummary } from "@/lib/types";
import UploadProgress from "@/components/UploadProgress";

const field =
  "w-full rounded-lg border border-line bg-paper px-4 py-3 text-sm outline-none transition focus:border-ink focus:ring-1 focus:ring-ink/10 disabled:opacity-50";

const focusOptions = [
  {
    id: "Repeated contact",
    title: "Repeated contact",
    description: "Unwanted messages, monitoring or persistent harassment.",
  },
  {
    id: "Threats or blackmail",
    title: "Threats or blackmail",
    description: "Threatening messages, demands or coercion.",
  },
  {
    id: "Intimate-image abuse",
    title: "Intimate-image abuse",
    description:
      "Threats to create or share intimate imagery, including fabricated imagery.",
  },
  {
    id: "Defamation or morphing",
    title: "Defamation or morphing",
    description:
      "Damaging claims or allegedly altered images that need context.",
  },
  {
    id: "Impersonation",
    title: "Impersonation",
    description: "Fake profiles or messages using another person's identity.",
  },
];

const steps = [
  "What happened",
  "Incident details",
  "Add evidence",
  "Review and save",
];

export default function NewReport() {
  const router = useRouter();
  const user = useUser();

  const [step, setStep] = useState(1);
  const [focus, setFocus] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const [caseMode, setCaseMode] = useState<"new" | "existing">("new");
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedCase, setSelectedCase] = useState("");
  const [casesLoading, setCasesLoading] = useState(false);
  const [casesError, setCasesError] = useState("");

  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user && !USE_MOCK) return;

    let cancelled = false;
    setCasesLoading(true);
    setCasesError("");

    listCases(emptyFilters, 1, 50)
      .then((result) => {
        if (!cancelled) setCases(result.items);
      })
      .catch((e) => {
        if (!cancelled) {
          setCasesError(
            e instanceof Error ? e.message : "Could not load your reports."
          );
        }
      })
      .finally(() => {
        if (!cancelled) setCasesLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [user]);

  if (!user && !USE_MOCK) {
    return (
      <main className="mx-auto mt-20 max-w-sm px-5 text-center">
        <p className="text-xs uppercase tracking-[0.2em] text-muted">
          Reporter workspace
        </p>
        <h1 className="mt-3 text-2xl font-semibold">Please log in first</h1>
        <p className="mt-2 text-sm text-muted">
          Sign in to document an incident and preserve your evidence.
        </p>
        <Link
          href="/login"
          className="mt-6 inline-block bg-ink px-6 py-3 text-sm text-paper transition hover:opacity-90"
        >
          Go to login
        </Link>
      </main>
    );
  }

  const chosenCase = cases.find((item) => item.id === selectedCase);

  function nextStep() {
    setError("");

    if (step === 1 && !focus) {
      setError("Please choose what best describes your situation.");
      return;
    }

    if (step === 2) {
      if (caseMode === "new" && !title.trim()) {
        setError("Please add a short title for your report.");
        return;
      }

      if (caseMode === "existing" && !selectedCase) {
        setError("Please select an existing report.");
        return;
      }
    }

    if (step === 3) {
      if (!file) {
        setError("Please select the evidence file you want to upload.");
        return;
      }

      if (file.size > 100 * 1024 * 1024) {
        setError("File is too large. Maximum size is 100 MB.");
        return;
      }
    }

    setStep((current) => Math.min(current + 1, 4));
  }

  async function submit() {
    if (!file) {
      setError("Please select an evidence file.");
      return;
    }

    if (file.size > 100 * 1024 * 1024) {
      setError("File is too large. Maximum size is 100 MB.");
      return;
    }

    setError("");
    setProgress(0);
    setBusy(true);

    try {
      let caseId = selectedCase;

      if (caseMode === "new") {
        const fullDescription = [
          `Reporting focus: ${focus}`,
          description.trim(),
        ]
          .filter(Boolean)
          .join("\n\n");

        const newCase = await createCase(title.trim(), fullDescription);
        caseId = newCase.id;
      }

      const receipt = await uploadEvidence(caseId, file, setProgress);

      router.replace(`/receipts/${receipt.evidenceId}`);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Something went wrong."
      );
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto mt-8 max-w-3xl px-4 pb-16 sm:px-6">
      {/* Header */}
      <header className="mb-10 border-b border-line pb-7">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted">
          Reporter workspace / New submission
        </p>

        <h1 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">
          Document an incident.
        </h1>

        <p className="mt-3 max-w-xl text-sm leading-7 text-muted">
          Start with what you already have. You can leave out details
          you are unsure about. You do not need to upload an alleged
          intimate image to document a threat.
        </p>
      </header>

      {/* Step progress */}
      <div className="mb-9">
        <div className="mb-4 flex items-center justify-between">
          <span className="text-xs font-medium text-ink">
            STEP 0{step} <span className="text-muted">/ 04</span>
          </span>
          <span className="text-xs text-muted">{steps[step - 1]}</span>
        </div>

        <div className="grid grid-cols-4 gap-2">
          {steps.map((label, index) => {
            const number = index + 1;
            const active = number === step;
            const completed = number < step;

            return (
              <button
                key={label}
                type="button"
                disabled={busy || number > step}
                onClick={() => {
                  setError("");
                  setStep(number);
                }}
                className="text-left disabled:cursor-default"
              >
                <div
                  className={`h-[3px] transition-colors duration-300 ${
                    active || completed ? "bg-ink" : "bg-line"
                  }`}
                />
                <span
                  className={`mt-2 block text-[10px] sm:text-xs ${
                    active
                      ? "font-semibold text-ink"
                      : completed
                        ? "text-ink"
                        : "text-muted"
                  }`}
                >
                  {label}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main form */}
      <section className="border border-line bg-paper">
        <div className="p-5 sm:p-8">
          {/* STEP 1 */}
          {step === 1 && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">
                01 — Reporting focus
              </p>

              <h2 className="mt-4 text-2xl font-semibold tracking-tight">
                What would you like to document?
              </h2>

              <p className="mt-2 text-sm leading-6 text-muted">
                Choose the focus that feels closest to your experience.
                These options guide review; they are not legal findings.
              </p>

              <div className="mt-7 divide-y divide-line border-y border-line">
                {focusOptions.map((option, index) => {
                  const selected = focus === option.id;

                  return (
                    <button
                      key={option.id}
                      type="button"
                      disabled={busy}
                      onClick={() => setFocus(option.id)}
                      className={`group flex w-full items-center justify-between gap-4 py-5 text-left transition ${
                        selected ? "pl-3 pr-2" : "px-1 hover:px-2"
                      }`}
                    >
                      <span className="flex min-w-0 items-start gap-4">
                        <span
                          className={`pt-0.5 text-xs tabular-nums ${
                            selected ? "text-ink" : "text-muted"
                          }`}
                        >
                          0{index + 1}
                        </span>

                        <span>
                          <span className="block text-sm font-medium">
                            {option.title}
                          </span>
                          <span className="mt-1 block text-xs leading-5 text-muted">
                            {option.description}
                          </span>
                        </span>
                      </span>

                      <span
                        className={`grid h-5 w-5 shrink-0 place-items-center rounded-full border text-xs transition ${
                          selected
                            ? "border-ink bg-ink text-paper"
                            : "border-line text-transparent group-hover:border-muted"
                        }`}
                      >
                        ✓
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* STEP 2 */}
          {step === 2 && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">
                02 — Incident details
              </p>

              <h2 className="mt-4 text-2xl font-semibold tracking-tight">
                Add a little context.
              </h2>

              <p className="mt-2 text-sm leading-6 text-muted">
                Keep it simple. Include only what you know.
              </p>

              <div className="mt-7">
                <p className="mb-3 text-sm font-medium">
                  Where should this evidence be saved?
                </p>

                <div className="grid grid-cols-2 gap-3">
                  {(["new", "existing"] as const).map((mode) => {
                    const selected = caseMode === mode;

                    return (
                      <button
                        key={mode}
                        type="button"
                        disabled={busy}
                        onClick={() => {
                          setCaseMode(mode);
                          if (mode === "new") setSelectedCase("");
                        }}
                        className={`border p-4 text-left transition ${
                          selected
                            ? "border-ink bg-card"
                            : "border-line hover:border-muted"
                        }`}
                      >
                        <span className="block text-sm font-medium">
                          {mode === "new" ? "New report" : "Existing report"}
                        </span>
                        <span className="mt-1 block text-xs text-muted">
                          {mode === "new"
                            ? "Start a new case"
                            : "Add evidence to a case"}
                        </span>
                        <span
                          className={`mt-4 block h-[2px] w-8 ${
                            selected ? "bg-ink" : "bg-line"
                          }`}
                        />
                      </button>
                    );
                  })}
                </div>
              </div>

              {caseMode === "new" ? (
                <div className="mt-7 space-y-5">
                  <div>
                    <label className="mb-2 block text-xs font-medium">
                      Report title
                    </label>
                    <input
                      className={field}
                      placeholder="E.g. Threatening messages on Instagram"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      disabled={busy}
                    />
                  </div>

                  <div>
                    <label className="mb-2 block text-xs font-medium">
                      Describe what happened
                    </label>
                    <textarea
                      className={`${field} min-h-36 resize-y`}
                      placeholder="What happened? Where did it happen? Include dates or account details only if you know them."
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      disabled={busy}
                    />
                  </div>
                </div>
              ) : (
                <div className="mt-7">
                  <label className="mb-2 block text-xs font-medium">
                    Select an existing report
                  </label>

                  {casesLoading ? (
                    <p className="py-4 text-sm text-muted">
                      Loading reports…
                    </p>
                  ) : cases.length > 0 ? (
                    <select
                      className={field}
                      value={selectedCase}
                      onChange={(e) => setSelectedCase(e.target.value)}
                      disabled={busy}
                    >
                      <option value="">Choose a report</option>
                      {cases.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.caseRef} — {item.title}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="border border-line bg-card p-4">
                      <p className="text-sm font-medium">
                        No existing reports available
                      </p>
                      <p className="mt-1 text-xs leading-5 text-muted">
                        {casesError ||
                          "You can start a new report instead."}
                      </p>
                    </div>
                  )}
                </div>
              )}

              <div className="mt-6 border-l-2 border-line pl-4">
                <p className="text-xs leading-6 text-muted">
                  Do not enter passwords, Aadhaar numbers or your full
                  home address. Uncertain details can be left out.
                </p>
              </div>
            </div>
          )}

          {/* STEP 3 */}
          {step === 3 && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">
                03 — Evidence
              </p>

              <h2 className="mt-4 text-2xl font-semibold tracking-tight">
                What evidence do you already have?
              </h2>

              <p className="mt-2 text-sm leading-6 text-muted">
                Upload the material available to you. Screenshots of
                threatening messages are valid evidence. You do not need
                to obtain or upload an alleged image.
              </p>

              <label className="mt-7 flex min-h-52 cursor-pointer flex-col items-center justify-center border border-dashed border-muted/50 bg-card p-6 text-center transition hover:border-ink">
                <span className="grid h-12 w-12 place-items-center border border-line bg-paper text-xl">
                  ↑
                </span>

                <span className="mt-4 text-sm font-medium text-ink">
                  {file ? "File selected" : "Choose a file to upload"}
                </span>

                <span className="mt-2 max-w-sm break-all text-xs text-muted">
                  {file
                    ? file.name
                    : "Select a document, screenshot, audio or video file"}
                </span>

                <span className="mt-3 text-[10px] uppercase tracking-wider text-muted">
                  JPG · PNG · WEBP · PDF · TXT · JSON · MP3 · WAV · M4A · MP4 · MOV · WEBM
                </span>

                <span className="mt-2 text-[10px] text-muted">
                  Maximum file size: 100 MB
                </span>

                <input
                  type="file"
                  className="hidden"
                  accept=".jpg,.jpeg,.png,.webp,.pdf,.txt,.json,.mp3,.wav,.m4a,.mp4,.mov,.webm"
                  disabled={busy}
                  onChange={(e) => {
                    setFile(e.target.files?.[0] ?? null);
                    setError("");
                  }}
                />
              </label>

              {file && (
                <div className="mt-5 flex items-center justify-between gap-3 border border-line p-4">
                  <div className="min-w-0">
                    <p className="text-[10px] uppercase tracking-wider text-muted">
                      Selected file
                    </p>
                    <p className="mt-1 truncate text-sm font-medium">
                      {file.name}
                    </p>
                    <p className="mt-1 text-xs text-muted">
                      {(file.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  </div>

                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => setFile(null)}
                    className="shrink-0 text-xs text-muted underline underline-offset-4 hover:text-ink"
                  >
                    Remove
                  </button>
                </div>
              )}
            </div>
          )}

          {/* STEP 4 */}
          {step === 4 && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">
                04 — Final review
              </p>

              <h2 className="mt-4 text-2xl font-semibold tracking-tight">
                Check before submitting.
              </h2>

              <p className="mt-2 text-sm leading-6 text-muted">
                Review your selected report and evidence file before saving.
              </p>

              <div className="mt-7 border-y border-line">
                <div className="grid gap-2 border-b border-line py-5 sm:grid-cols-[150px_1fr]">
                  <p className="text-xs text-muted">Reporting focus</p>
                  <p className="text-sm font-medium">{focus}</p>
                </div>

                <div className="grid gap-2 border-b border-line py-5 sm:grid-cols-[150px_1fr]">
                  <p className="text-xs text-muted">Destination</p>
                  <p className="text-sm font-medium">
                    {caseMode === "new"
                      ? `New report: ${title}`
                      : chosenCase
                        ? `${chosenCase.caseRef} — ${chosenCase.title}`
                        : "No report selected"}
                  </p>
                </div>

                {caseMode === "new" && description && (
                  <div className="grid gap-2 border-b border-line py-5 sm:grid-cols-[150px_1fr]">
                    <p className="text-xs text-muted">Incident details</p>
                    <p className="whitespace-pre-wrap text-sm leading-6">
                      {description}
                    </p>
                  </div>
                )}

                <div className="grid gap-2 py-5 sm:grid-cols-[150px_1fr]">
                  <p className="text-xs text-muted">Evidence file</p>
                  <div>
                    <p className="break-all text-sm font-medium">
                      {file?.name}
                    </p>
                    {file && (
                      <p className="mt-1 text-xs text-muted">
                        {(file.size / (1024 * 1024)).toFixed(2)} MB
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {caseMode === "existing" && (
                <p className="mt-4 border-l-2 border-line pl-4 text-xs leading-5 text-muted">
                  The selected focus is for this form only. Adding evidence
                  to an existing report does not change that report's details.
                </p>
              )}

              <div className="mt-6 bg-card p-4">
                <p className="text-xs font-semibold">Evidence integrity</p>
                <p className="mt-2 text-xs leading-6 text-muted">
                  When you submit, the file will be uploaded and a
                  fingerprinted evidence receipt will be generated.
                  The fingerprint helps show whether the saved file
                  changes after upload. It does not prove that the
                  content itself is true.
                </p>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div
              role="alert"
              className="mt-6 border-l-2 border-red-600 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {error}
            </div>
          )}

          {/* Upload progress */}
          {busy && (
            <div className="mt-7 space-y-3 border-t border-line pt-5">
              <div className="flex justify-between text-xs">
                <span className="font-medium">Uploading evidence…</span>
                <span className="tabular-nums text-muted">{progress}%</span>
              </div>

              <UploadProgress percent={progress} />

              <p className="text-xs leading-5 text-muted">
                Please keep this page open. Your receipt will open
                automatically when the upload completes.
              </p>
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between border-t border-line bg-card px-5 py-5 sm:px-8">
          <button
            type="button"
            disabled={step === 1 || busy}
            onClick={() => {
              setError("");
              setStep((current) => Math.max(current - 1, 1));
            }}
            className="text-sm text-muted underline underline-offset-4 transition hover:text-ink disabled:opacity-30"
          >
            ← Back
          </button>

          {step < 4 ? (
            <button
              type="button"
              disabled={busy}
              onClick={nextStep}
              className="bg-ink px-7 py-3 text-sm font-medium text-paper transition hover:opacity-85 disabled:opacity-50"
            >
              Continue →
            </button>
          ) : (
            <button
              type="button"
              onClick={submit}
              disabled={busy || !file}
              className="bg-ink px-7 py-3 text-sm font-medium text-paper transition hover:opacity-85 disabled:opacity-50"
            >
              {busy ? "Saving…" : "Submit and save evidence"}
            </button>
          )}
        </div>
      </section>

      <p className="mt-5 text-center text-xs leading-5 text-muted">
        Your evidence is handled privately. You remain in control of
        whether to take any further reporting action.
      </p>
    </main>
  );
}
