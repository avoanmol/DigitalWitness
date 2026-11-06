
"use client";

import { useState } from "react";
import { reviewFlag } from "@/lib/api";
import type { Flag, ReviewStatus } from "@/lib/types";
import { threatLabels } from "@/lib/labels";
import { SeverityPill } from "@/components/StatusPill";
import ConfidenceMeter from "@/components/ConfidenceMeter";
import ReviewButtons from "@/components/ReviewButtons";

type Props = {
  flag: Flag;
  canReview: boolean;
  onChange: (id: string, status: ReviewStatus) => void;
};

export default function FlagCard({
  flag,
  canReview,
  onChange,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function decide(status: "confirmed" | "rejected") {
    setBusy(true);
    setError("");

    try {
      await reviewFlag(flag.id, status);
      onChange(flag.id, status);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Could not save your decision"
      );
    } finally {
      setBusy(false);
    }
  }

  const reviewed = flag.reviewStatus !== "pending";

  return (
    <article
      className={`border-t-2 border-[#D8D5CD] py-5 transition-opacity ${
        flag.reviewStatus === "rejected" ? "opacity-60" : ""
      }`}
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <SeverityPill severity={flag.severity} />

        <h3 className="text-sm font-semibold text-[#242424]">
          {threatLabels[flag.threatClass]}
        </h3>

        <span className="ml-auto text-[10px] uppercase tracking-[0.14em] text-[#88847B]">
          AI suggestion
        </span>
      </div>

      <div className="mt-5 border-l-2 border-[#AD841E] bg-[#F8F6F0] px-5 py-4">
        <p className="mb-2 text-[10px] uppercase tracking-[0.14em] text-[#88847B]">
          Matched excerpt
        </p>

        <blockquote className="whitespace-pre-wrap break-words text-sm leading-7 text-[#333]">
          “{flag.snippet}”
        </blockquote>
      </div>

      {flag.reason && (
        <p className="mt-4 text-sm leading-6 text-[#77736B]">
          {flag.reason}
        </p>
      )}

      <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
        <ConfidenceMeter value={flag.confidence} />

        {flag.reviewStatus === "confirmed" && (
          <span className="border border-emerald-200 px-3 py-1.5 text-xs font-medium text-emerald-800">
            Confirmed by a reviewer
          </span>
        )}

        {flag.reviewStatus === "rejected" && (
          <span className="border border-[#D8D5CD] px-3 py-1.5 text-xs text-[#77736B]">
            Rejected by a reviewer
          </span>
        )}

        {flag.reviewStatus === "pending" && canReview && (
          <ReviewButtons
            busy={busy}
            onConfirm={() => decide("confirmed")}
            onReject={() => decide("rejected")}
          />
        )}

        {flag.reviewStatus === "pending" && !canReview && (
          <span className="text-xs text-[#88847B]">
            Awaiting review
          </span>
        )}
      </div>

      {reviewed && (
        <p className="mt-3 text-[10px] uppercase tracking-[0.12em] text-[#88847B]">
          Human review recorded
        </p>
      )}

      {error && (
        <p role="alert" className="mt-3 text-xs text-red-600">
          {error}
        </p>
      )}
    </article>
  );
}
