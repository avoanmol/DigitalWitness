
"use client";

import { useState } from "react";
import Link from "next/link";
import { reviewLink } from "@/lib/api";
import type { CaseLink, LinkStatus } from "@/lib/types";
import { entityLabels } from "@/lib/labels";
import ConfidenceMeter from "@/components/ConfidenceMeter";
import ReviewButtons from "@/components/ReviewButtons";

type Props = {
  link: CaseLink;
  canReview: boolean;
  onChange: (id: string, status: LinkStatus) => void;
};

export default function LinkCard({ link, canReview, onChange }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function decide(status: "confirmed" | "rejected") {
    setBusy(true);
    setError("");

    try {
      await reviewLink(link.id, status);
      onChange(link.id, status);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not save your decision",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <article
      className={`border-t border-[#D8D5CD] py-5 transition ${
        link.status === "rejected" ? "opacity-60" : ""
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-[#777777]">Potential connection</span>

        <Link
          href={`/cases/${link.otherCaseId}`}
          className="text-sm font-semibold text-[#242424] underline underline-offset-4 hover:text-[#AD841E]"
        >
          {link.otherCaseRef}
        </Link>

        {link.createdBy === "ai" && (
          <span className="ml-auto text-xs text-[#8A681B]">
            AI suggestion
          </span>
        )}
      </div>

      <p className="mt-5 text-xs uppercase tracking-[0.12em] text-[#888888]">
        Shared indicators
      </p>

      <div className="mt-2 divide-y divide-[#E5E2DA]">
        {link.sharedEntities.map((entity, index) => (
          <div
            key={`${entity.type}-${entity.value}-${index}`}
            className="flex flex-wrap gap-x-3 gap-y-1 py-2 text-sm"
          >
            <span className="w-24 shrink-0 text-xs text-[#888888]">
              {entityLabels[entity.type] ?? entity.type}
            </span>
            <span className="break-all text-[#242424]">{entity.value}</span>
          </div>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
        <ConfidenceMeter value={link.confidence} />

        {link.status === "confirmed" && (
          <span className="text-xs font-medium text-emerald-700">
            Confirmed link
          </span>
        )}

        {link.status === "rejected" && (
          <span className="text-xs text-[#777777]">
            Rejected
          </span>
        )}

        {link.status === "suggested" && canReview && (
          <ReviewButtons
            busy={busy}
            onConfirm={() => decide("confirmed")}
            onReject={() => decide("rejected")}
          />
        )}

        {link.status === "suggested" && !canReview && (
          <span className="text-xs text-[#777777]">Awaiting review</span>
        )}
      </div>

      {error && (
        <p className="mt-3 text-xs text-red-600" role="alert">
          {error}
        </p>
      )}
    </article>
  );
}
