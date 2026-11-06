
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getAnalysis,
  getCase,
  getCaseLinks,
  listCases,
  USE_MOCK,
} from "@/lib/api";
import { useUser } from "@/lib/auth";
import { emptyFilters } from "@/components/FilterBar";
import { useCanReview } from "@/lib/useCanReview";
import type { Analysis, CaseLink, Flag } from "@/lib/types";

type InsightData = {
  analyses: Analysis[];
  links: CaseLink[];
};

export default function InsightsPage() {
  const user = useUser();
  const canReview = useCanReview();

  const [data, setData] = useState<InsightData>({
    analyses: [],
    links: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user && !USE_MOCK) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function loadInsights() {
      try {
        const casesPage = await listCases(emptyFilters, 1, 100);

        const caseDetails = await Promise.all(
          casesPage.items.map((item) => getCase(item.id))
        );

        const evidenceItems = caseDetails.flatMap((item) => item.evidence);

        const [analysisResults, linkResults] = await Promise.all([
          Promise.all(
            evidenceItems.map((item) =>
              getAnalysis(item.id).catch(() => null)
            )
          ),
          Promise.all(
            caseDetails.map((item) =>
              getCaseLinks(item.id).catch(() => [])
            )
          ),
        ]);

        if (cancelled) return;

        setData({
          analyses: analysisResults.filter(
            (item): item is Analysis => item !== null
          ),
          links: linkResults.flat(),
        });
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof Error
              ? e.message
              : "Could not load review insights."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadInsights();

    return () => {
      cancelled = true;
    };
  }, [user]);

  if (!user && !USE_MOCK) {
    return (
      <main className="mx-auto mt-16 max-w-sm text-center">
        <h1 className="text-2xl font-semibold">Please log in first</h1>
        <Link
          href="/login"
          className="mt-4 inline-block bg-ink px-6 py-2 text-paper"
        >
          Go to login
        </Link>
      </main>
    );
  }

  if (user && user.role !== "investigator" &&
      user.role !== "admin" && user.role !== "legal") {
    return (
      <main className="mx-auto mt-16 max-w-sm text-center">
        <h1 className="text-2xl font-semibold">Access restricted</h1>
        <p className="mt-2 text-sm text-muted">
          Review insights are available to authorised reviewers.
        </p>
      </main>
    );
  }

  const allFlags: Flag[] = data.analyses.flatMap(
    (analysis) => analysis.flags
  );

  const pendingFlags = allFlags.filter(
    (flag) => flag.reviewStatus === "pending"
  ).length;

  const confirmedFlags = allFlags.filter(
    (flag) => flag.reviewStatus === "confirmed"
  ).length;

  const rejectedFlags = allFlags.filter(
    (flag) => flag.reviewStatus === "rejected"
  ).length;

  const suggestedLinks = data.links.filter(
    (link) => link.status === "suggested"
  );

  const confirmedLinks = data.links.filter(
    (link) => link.status === "confirmed"
  );

  const uniqueLinks = Array.from(
    new Map(data.links.map((link) => [link.id, link])).values()
  );

  return (
    <main className="mt-8 space-y-8">
      <header className="fade-up">
        <p className="text-xs uppercase tracking-[0.2em] text-muted">
          Review workspace
        </p>
        <h1 className="mt-2 text-3xl font-semibold sm:text-4xl">
          Review insights
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-muted">
          An overview of AI-generated review leads and suggested
          connections across the available cases.
        </p>
      </header>

      {USE_MOCK && (
        <p className="border border-line bg-card p-3 text-xs text-muted">
          Demo mode — figures are based on synthetic demonstration data.
        </p>
      )}

      {error && (
        <p className="border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </p>
      )}

      {loading ? (
        <p className="py-12 text-center text-sm text-muted">
          Loading review insights...
        </p>
      ) : (
        <>
          <section>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">AI review flags</h2>
              <span className="text-xs text-muted">
                {allFlags.length} total
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Metric label="Total flags" value={allFlags.length} />
              <Metric label="Awaiting review" value={pendingFlags} />
              <Metric label="Confirmed" value={confirmedFlags} />
              <Metric label="Rejected" value={rejectedFlags} />
            </div>
          </section>

          <section>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Case connections</h2>
              <span className="text-xs text-muted">
                {uniqueLinks.length} total
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Metric
                label="Suggested connections"
                value={suggestedLinks.length}
              />
              <Metric
                label="Confirmed connections"
                value={confirmedLinks.length}
              />
            </div>
          </section>

          <section>
            <h2 className="mb-4 text-lg font-semibold">
              Recent AI flags
            </h2>

            {allFlags.length === 0 ? (
              <EmptyState message="No AI flags are available yet." />
            ) : (
              <div className="divide-y divide-line border-y border-line">
                {allFlags.slice(0, 8).map((flag) => (
                  <article key={flag.id} className="py-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-semibold capitalize">
                        {flag.threatClass.replaceAll("_", " ")}
                      </p>
                      <span className="text-xs text-muted capitalize">
                        {flag.reviewStatus}
                      </span>
                    </div>

                    <p className="mt-2 text-sm text-muted">
                      {flag.snippet}
                    </p>

                    <p className="mt-2 text-xs text-muted">
                      Severity: {flag.severity} · Confidence:{" "}
                      {Math.round(flag.confidence * 100)}%
                    </p>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section>
            <h2 className="mb-4 text-lg font-semibold">
              Suggested case connections
            </h2>

            {uniqueLinks.length === 0 ? (
              <EmptyState message="No case connections are available yet." />
            ) : (
              <div className="divide-y divide-line border-y border-line">
                {uniqueLinks.slice(0, 8).map((link) => (
                  <article
                    key={link.id}
                    className="flex flex-wrap items-center justify-between gap-3 py-4"
                  >
                    <div>
                      <p className="text-sm font-semibold">
                        {link.otherCaseRef}
                      </p>
                      <p className="mt-1 text-xs text-muted">
                        {link.sharedEntities.length} shared identifiers
                        {" · "}
                        {Math.round(link.confidence * 100)}% confidence
                      </p>
                    </div>

                    <span className="text-xs capitalize text-muted">
                      {link.status}
                    </span>
                  </article>
                ))}
              </div>
            )}
          </section>

          {!canReview && (
            <p className="border border-line bg-card p-4 text-xs text-muted">
              Read-only view. Only investigators and administrators can
              confirm or reject review suggestions.
            </p>
          )}

          <p className="text-xs text-muted">
            AI flags and shared identifiers are review leads, not findings
            of guilt or proof of authenticity. Human review is required.
          </p>
        </>
      )}
    </main>
  );
}

function Metric({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div className="border border-line bg-card p-4">
      <p className="text-2xl font-semibold tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-muted">{label}</p>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <p className="border border-line bg-card p-6 text-sm text-muted">
      {message}
    </p>
  );
}
