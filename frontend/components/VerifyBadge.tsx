import type { VerifyResult } from "@/lib/types";
import { formatIST } from "@/lib/format";

const COPY: Record<
  VerifyResult,
  {
    title: string;
    body: string;
    note?: string;
    dot: string;
    style: string;
  }
> = {
  verified: {
    title: "Verified",
    body: "Unchanged since anchoring.",
    note: "This does not prove the content was true before it was uploaded.",
    dot: "bg-emerald-600",
    style: "border-emerald-200 bg-emerald-50 text-emerald-900",
  },
  altered: {
    title: "Altered",
    body: "This file no longer matches what was recorded and anchored. Do not rely on it.",
    dot: "bg-red-600",
    style: "border-red-200 bg-red-50 text-red-900",
  },
  pending: {
    title: "Pending anchor",
    body: "Not anchored yet. The file is stored and fingerprinted; anchoring is queued.",
    dot: "bg-amber-600",
    style: "border-amber-200 bg-amber-50 text-amber-900",
  },
  error: {
    title: "Could not verify",
    body: "Verification could not be completed. Try again; this is not a finding about the file.",
    dot: "bg-neutral-500",
    style: "border-neutral-300 bg-neutral-50 text-neutral-800",
  },
};

const NONE = {
  title: "Not checked yet",
  body: "Press Verify to compare this file with the blockchain record.",
  note: undefined,
  dot: "bg-neutral-400",
  style: "border-neutral-300 bg-white text-neutral-600",
};

type Props = {
  result: VerifyResult | null;
  loading?: boolean;
  message?: string;
  checkedAt?: string;
  compact?: boolean;
};

export default function VerifyBadge({
  result,
  loading,
  message,
  checkedAt,
  compact,
}: Props) {
  const c = result ? COPY[result] : NONE;

  if (compact) {
    return (
      <span
        className={`inline-flex items-center gap-2 border px-3 py-1 text-xs font-medium ${c.style}`}
      >
        <span className={`h-2 w-2 ${c.dot}`} />
        {result ? c.title : "Not checked"}
      </span>
    );
  }

  if (loading) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="border border-[#D8C18A] bg-[#FBF7EC] p-5 text-[#725719]"
      >
        <div className="flex items-center gap-3">
          <span className="h-2.5 w-2.5 animate-pulse bg-[#AD841E]" />
          <p className="text-base font-semibold">Checking...</p>
        </div>

        <p className="mt-3 text-sm">
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
      className={`border p-5 ${c.style}`}
    >
      <div className="flex items-center gap-3">
        <span className={`h-2.5 w-2.5 ${c.dot}`} />
        <p className="text-base font-semibold">{c.title}</p>
      </div>

      <p className="mt-3 text-sm leading-6">{body}</p>

      {c.note && (
        <p className="mt-3 border-t border-current/15 pt-3 text-xs leading-5 opacity-80">
          {c.note}
        </p>
      )}

      {checkedAt && (
        <p
          className="mt-3 text-xs opacity-70"
          title={`${checkedAt} (UTC)`}
        >
          Checked {formatIST(checkedAt)}
        </p>
      )}
    </div>
  );
}