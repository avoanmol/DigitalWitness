
"use client";

import { useEffect, useState } from "react";
import { getAnalysis } from "@/lib/api";
import { useCanReview } from "@/lib/useCanReview";
import type { Analysis, ReviewStatus } from "@/lib/types";
import { entityLabels } from "@/lib/labels";
import FlagCard from "@/components/FlagCard";

const NOT_READY: Record<string, string> = {
  queued: "AI analysis is queued. Check again in a moment.",
  running: "AI analysis is running. Check again in a moment.",
  failed:
    "AI analysis failed for this file. The evidence itself is safe and unchanged.",
};

export default function AnalysisPanel({
  evidenceId,
}: {
  evidenceId: string;
}) {
  const canReview = useCanReview();
  const [data, setData] = useState<Analysis | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    setData(null);
    setError("");

    getAnalysis(evidenceId)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(
            e instanceof Error
              ? e.message
              : "Could not load the AI analysis"
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [evidenceId]);

  function updateFlag(id: string, status: ReviewStatus) {
    setData((current) =>
      current
        ? {
            ...current,
            flags: current.flags.map((flag) =>
              flag.id === id
                ? { ...flag, reviewStatus: status }
                : flag
            ),
          }
        : current
    );
  }

  return (
    <section className="w-full">
      <div className="mb-10 flex flex-wrap items-start justify-between gap-5">
        <div>
          <p className="mb-3 text-xs font-medium uppercase tracking-[0.18em] text-[#AD841E]">
            Intelligence review
          </p>

          <h2 className="text-3xl font-semibold tracking-tight text-[#242424] sm:text-4xl">
            AI Analysis
          </h2>

          <p className="mt-3 max-w-2xl text-sm leading-7 text-[#77736B]">
            Automated findings help identify relevant details and possible
            threats. These are leads, not verdicts. A person must review
            and confirm them.
          </p>
        </div>

        {data && (
          <span className="border border-[#DDD9D0] px-3 py-2 text-xs uppercase tracking-[0.1em] text-[#77736B]">
            {data.status === "done"
              ? "Analysis complete"
              : data.status}
          </span>
        )}
      </div>

      {error && (
        <p
          role="alert"
          className="border-l-2 border-red-600 bg-red-50 px-5 py-4 text-sm text-red-700"
        >
          {error}
        </p>
      )}

      {!data && !error && (
        <div
          className="space-y-4"
          aria-busy="true"
          aria-label="Loading AI analysis"
        >
          <div className="h-4 w-40 animate-pulse bg-[#E5E2DA]" />
          <div className="h-3 w-full max-w-lg animate-pulse bg-[#E5E2DA]" />
          <div className="h-3 w-3/4 max-w-lg animate-pulse bg-[#E5E2DA]" />
        </div>
      )}

      {data && data.status !== "done" && (
        <p className="border-l-2 border-[#AD841E] bg-[#F8F6F0] px-5 py-4 text-sm leading-6 text-[#77736B]">
          {NOT_READY[data.status] ??
            "AI analysis is not ready yet."}
        </p>
      )}

      {data && data.status === "done" && (
        <div className="space-y-12">
          <section>
            <div className="flex items-center justify-between border-b border-[#D8D5CD] pb-4">
              <h3 className="text-lg font-semibold text-[#242424]">
                Extracted entities
              </h3>

              <span className="text-xs text-[#88847B]">
                {data.entities.length} found
              </span>
            </div>

            {data.entities.length === 0 ? (
              <p className="py-6 text-sm text-[#77736B]">
                No phone numbers, handles, emails or links found.
              </p>
            ) : (
              <div className="grid gap-x-8 sm:grid-cols-2">
                {data.entities.map((entity) => (
                  <div
                    key={entity.id}
                    className="border-b border-[#E5E2DA] py-5"
                    title={`Normalised: ${entity.normalised} · ${Math.round(
                      entity.confidence * 100
                    )}% confidence`}
                  >
                    <p className="mb-2 text-[11px] uppercase tracking-[0.14em] text-[#88847B]">
                      {entityLabels[entity.type] ?? entity.type}
                    </p>

                    <p className="break-all text-sm font-medium text-[#242424]">
                      {entity.raw}
                    </p>

                    <p className="mt-2 text-xs text-[#88847B]">
                      {Math.round(entity.confidence * 100)}% confidence
                    </p>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section>
            <div className="flex items-center justify-between border-b border-[#D8D5CD] pb-4">
              <h3 className="text-lg font-semibold text-[#242424]">
                Possible threats
              </h3>

              <span className="text-xs text-[#88847B]">
                {data.flags.length} flagged
              </span>
            </div>

            {data.flags.length === 0 ? (
              <p className="py-6 text-sm text-[#77736B]">
                No possible threats were flagged.
              </p>
            ) : (
              <div className="mt-6 grid gap-5 lg:grid-cols-2">
                {data.flags.map((flag) => (
                  <FlagCard
                    key={flag.id}
                    flag={flag}
                    canReview={canReview}
                    onChange={updateFlag}
                  />
                ))}
              </div>
            )}
          </section>

          {data.text && (
            <section className="border-t border-[#D8D5CD] pt-6">
              <details className="group">
                <summary className="flex cursor-pointer items-center justify-between gap-4 text-sm font-semibold text-[#242424]">
                  <span>
                    Text read from the file
                    {data.language
                      ? ` (${data.language})`
                      : ""}
                  </span>

                  <span className="text-xl font-normal text-[#AD841E] transition-transform group-open:rotate-45">
                    +
                  </span>
                </summary>

                <pre className="mt-6 max-h-80 overflow-auto whitespace-pre-wrap break-words border-l-2 border-[#D8D5CD] bg-[#F8F7F3] p-5 text-xs leading-6 text-[#555]">
                  {data.text}
                </pre>
              </details>
            </section>
          )}
        </div>
      )}
    </section>
  );
}
