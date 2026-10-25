"use client";
import { useState } from "react";
import Link from "next/link";
import { createCase, uploadEvidence, USE_MOCK } from "@/lib/api";
import { useUser } from "@/lib/auth";
import type { Receipt } from "@/lib/types";
import ReceiptCard from "@/components/ReceiptCard";
import UploadProgress from "@/components/UploadProgress";

const chips = ["Fingerprinted on arrival", "Encrypted", "Read-only"];
const field =
  "w-full rounded-2xl border border-line bg-paper p-3 outline-none transition focus:border-ink";

export default function NewReport() {
  const user = useUser();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState<Receipt | null>(null);

  async function submit() {
    if (!title || !file) { setError("Please add a title and a file."); return; }
    if (file.size > 100 * 1024 * 1024) { setError("File is too large (max 100 MB)."); return; }
    setError(""); setBusy(true);
    try {
      const c = await createCase(title, description);
      setReceipt(await uploadEvidence(c.id, file, setProgress));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally { setBusy(false); }
  }

  if (!user && !USE_MOCK) {
    return (
      <main className="mx-auto mt-16 max-w-sm text-center">
        <h1 className="text-2xl font-semibold">Please log in first</h1>
        <Link href="/login"
          className="mt-4 inline-block rounded-full bg-ink px-6 py-2 text-paper">
          Go to login
        </Link>
      </main>
    );
  }

  if (receipt) {
    return (
      <>
        <ReceiptCard receipt={receipt} />
        <p className="mt-4 text-center text-sm">
          <Link href={`/receipts/${receipt.evidenceId}`}
            className="text-muted underline hover:text-ink">
            Open receipt page
          </Link>
        </p>
      </>
    );
  }

  return (
    <main className="mt-8 grid gap-4 lg:grid-cols-5">
      <section className="lg:col-span-3">
        <div className="fade-up grid grid-cols-2 gap-3">
          <div className="rounded-3xl bg-ink p-5 text-paper">
            <p className="text-2xl font-semibold">Hash first</p>
            <p className="mt-1 text-xs text-white/60">
              Your file is fingerprinted before anything else happens
            </p>
          </div>
          <div className="rounded-3xl bg-card p-5">
            <p className="text-2xl font-semibold">{"< 3 min"}</p>
            <p className="mt-1 text-xs text-muted">From form to receipt</p>
          </div>
        </div>

        <h1
          className="fade-up mt-8 text-4xl font-semibold leading-tight sm:text-5xl"
          style={{ animationDelay: "80ms" }}
        >
          Save your evidence. Show it hasn’t changed.
        </h1>
        <p className="fade-up mt-4 max-w-lg text-sm text-muted"
          style={{ animationDelay: "160ms" }}>
          Upload a screenshot, PDF, chat export, audio or video. You get a receipt you can
          keep. It shows a file is unchanged since upload, not that its content is true.
        </p>
        <div className="fade-up mt-6 flex flex-wrap gap-2" style={{ animationDelay: "240ms" }}>
          {chips.map((c) => (
            <span key={c} className="rounded-full bg-card px-3 py-1.5 text-xs text-muted">
              {c}
            </span>
          ))}
        </div>
      </section>

      <section
        className="fade-up space-y-3 rounded-3xl bg-card p-5 lg:col-span-2"
        style={{ animationDelay: "120ms" }}
      >
        <input className={field} placeholder="Short title" value={title}
          onChange={(e) => setTitle(e.target.value)} />
        <textarea className={`${field} h-28`} placeholder="What happened?" value={description}
          onChange={(e) => setDescription(e.target.value)} />

        <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-muted/50 bg-paper p-6 text-center text-sm text-muted transition hover:border-ink">
          {file ? file.name : "Tap to choose a file"}
          <input
            type="file"
            className="hidden"
            accept=".jpg,.jpeg,.png,.webp,.pdf,.txt,.json,.mp3,.wav,.m4a,.mp4,.mov,.webm"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>

        {busy && <UploadProgress percent={progress} />}
        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          onClick={submit}
          disabled={busy}
          className="group flex w-full items-center justify-between rounded-full bg-ink py-2 pl-6 pr-2 text-paper transition disabled:opacity-50"
        >
          <span>{busy ? `Uploading ${progress}%` : "Save my evidence"}</span>
          <span className="grid h-10 w-10 place-items-center rounded-full bg-paper text-ink transition group-hover:translate-x-0.5">
            →
          </span>
        </button>
      </section>
    </main>
  );
}