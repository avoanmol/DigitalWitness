import type { VerifyResult } from "@/lib/types";
import { formatIST } from "@/lib/format";

const COPY: Record<
  VerifyResult,
  { title: string; body: string; note?: string; dot: string; box: string }
> = {
  verified: {
    title: "Verified",
    body: "Unchanged since anchoring.",
    note: "This does not prove the content was true before it was uploaded.",
    dot: "bg-emerald-500",
    box: "bg-emerald-50 border-emerald-200 text-emerald-900",
  },
  altered: {
    title: "Altered",
    body: "This file no longer matches what was recorded and anchored. Do not rely on it.",
    dot: "bg-red-500",
    box: "bg-red-50 border-red-200 text-red-900",
  },
  pending: {
    title: "Pending anchor",
    body: "Not anchored yet. The file is stored and fingerprinted; anchoring is queued.",
    dot: "bg-amber-500",
    box: "bg-amber-50 border-amber-200 text-amber-900",
  },
  error: {
    title: "Could not verify",
    body: "Verification could not be completed. Try again; this is not a finding about the file.",
    dot: "bg-neutral-400",
    box: "bg-neutral-100 border-neutral-300 text-neutral-800",
  },
};

const NONE = {
  title: "Not checked yet",
  body: "Press Verify to compare this file with the blockchain record.",
  note: undefined,
  dot: "bg-neutral-300",
  box: "bg-paper border-dashed border-line text-muted",
};

type Props = {
  result: VerifyResult | null;
  loading?: boolean;
  message?: string;
  checkedAt?: string;
  compact?: boolean;
};

export default function VerifyBadge({ result, loading, message, checkedAt, compact }: Props) {
  const c = result ? COPY[result] : NONE;

  if (compact) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${c.box}`}
      >
        <span className={`h-2 w-2 rounded-full ${c.dot}`} />
        {result ? c.title : "Not checked"}
      </span>
    );
  }

  if (loading) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="rounded-3xl border border-line bg-card p-5 text-ink"
      >
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 animate-pulse rounded-full bg-accent" />
          <p className="text-lg font-semibold">Checking…</p>
        </div>
        <p className="mt-2 text-sm text-muted">
          Comparing the stored file with the blockchain record.
        </p>
      </div>
    );
  }

  const body = result === "verified" && message ? message : c.body;

  return (
    <div
      key={result ?? "none"}
      role="status"
      aria-live="polite"
      className={`pop rounded-3xl border p-5 ${c.box}`}
    >
      <div className="flex items-center gap-2">
        <span className={`h-3 w-3 rounded-full ${c.dot}`} />
        <p className="text-lg font-semibold">{c.title}</p>
      </div>
      <p className="mt-2 text-sm">{body}</p>
      {c.note && <p className="mt-2 text-xs opacity-80">{c.note}</p>}
      {checkedAt && (
        <p className="mt-3 text-xs opacity-70" title={`${checkedAt} (UTC)`}>
          Checked {formatIST(checkedAt)}
        </p>
      )}
    </div>
  );
}