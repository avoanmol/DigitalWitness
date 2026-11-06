
"use client";

import Link from "next/link";
import type { CaseSummary, Page } from "@/lib/types";
import { threatLabels } from "@/lib/labels";
import { formatIST } from "@/lib/format";
import { SeverityPill, StatusPill } from "@/components/StatusPill";
import VerifyBadge from "@/components/VerifyBadge";

type Props = {
  data: Page<CaseSummary> | null;
  loading: boolean;
  error: string;
  onPage: (page: number) => void;
};

function TableMessage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="border border-line bg-paper px-6 py-14 text-center">
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      <p className="mt-2 text-sm text-muted">{description}</p>
    </div>
  );
}

export default function CaseTable({
  data,
  loading,
  error,
  onPage,
}: Props) {
  if (error) {
    return (
      <div
        role="alert"
        className="border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-800"
      >
        <p className="font-semibold">Unable to load cases</p>
        <p className="mt-1">{error}</p>
      </div>
    );
  }

  if (loading && !data) {
    return (
      <div
        className="space-y-3 border border-line bg-paper p-5"
        aria-busy="true"
        aria-label="Loading cases"
      >
        <div className="h-5 w-40 animate-pulse bg-line" />
        {[0, 1, 2, 3].map((item) => (
          <div
            key={item}
            className="h-12 animate-pulse border-t border-line bg-card"
          />
        ))}
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <TableMessage
        title="No cases found"
        description="Try changing or clearing the filters to see other submissions."
      />
    );
  }

  const pages = Math.max(1, Math.ceil(data.total / data.pageSize));

  const buttonClass =
    "border border-line px-4 py-2 text-sm text-ink transition hover:border-ink hover:bg-ink hover:text-paper disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-line disabled:hover:bg-transparent disabled:hover:text-ink";

  return (
    <section aria-label="Case register">
      <div
        className={`border border-line bg-paper transition-opacity ${
          loading ? "opacity-60" : "opacity-100"
        }`}
      >
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-4 sm:px-5">
          <div>
            <h3 className="text-sm font-semibold text-ink">
              Submitted cases
            </h3>
            <p className="mt-1 text-xs text-muted">
              Select a case reference to inspect its record.
            </p>
          </div>

          <span className="text-xs tabular-nums text-muted">
            {data.total} total records
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="border-b border-line bg-card text-[11px] font-medium uppercase tracking-[0.1em] text-muted">
              <tr>
                <th className="px-4 py-3 sm:px-5">Case reference</th>
                <th className="px-4 py-3">Case title</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Severity</th>
                <th className="px-4 py-3">Threat types</th>
                <th className="px-4 py-3">Integrity</th>
                <th className="px-4 py-3">Files</th>
                <th className="px-4 py-3">Created</th>
              </tr>
            </thead>

            <tbody>
              {data.items.map((item) => (
                <tr
                  key={item.id}
                  className="border-b border-line last:border-b-0 transition-colors hover:bg-card/70"
                >
                  <td className="px-4 py-4 sm:px-5">
                    <Link
                      href={`/cases/${item.id}`}
                      className="font-semibold text-ink underline-offset-4 hover:underline"
                    >
                      {item.caseRef}
                    </Link>
                  </td>

                  <td className="max-w-[220px] px-4 py-4">
                    <Link
                      href={`/cases/${item.id}`}
                      className="block truncate font-medium text-ink underline-offset-4 hover:underline"
                      title={item.title}
                    >
                      {item.title}
                    </Link>
                  </td>

                  <td className="px-4 py-4">
                    <StatusPill status={item.status} />
                  </td>

                  <td className="px-4 py-4">
                    {item.topSeverity ? (
                      <SeverityPill severity={item.topSeverity} />
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </td>

                  <td className="max-w-[190px] px-4 py-4 text-xs leading-5 text-muted">
                    {item.threatClasses.length > 0
                      ? item.threatClasses
                          .map((type) => threatLabels[type] ?? type)
                          .join(", ")
                      : "—"}
                  </td>

                  <td className="px-4 py-4">
                    <VerifyBadge
                      result={item.verification}
                      compact
                    />
                  </td>

                  <td className="px-4 py-4 tabular-nums text-ink">
                    {item.evidenceCount}
                  </td>

                  <td
                    className="whitespace-nowrap px-4 py-4 text-xs text-muted"
                    title={`${item.createdAt} (UTC)`}
                  >
                    {formatIST(item.createdAt)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {loading && (
          <div className="border-t border-line px-5 py-2 text-xs text-muted">
            Updating results…
          </div>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted">
          Page <span className="font-medium text-ink">{data.page}</span> of{" "}
          <span className="font-medium text-ink">{pages}</span>
          <span className="mx-2">·</span>
          {data.total} cases
        </p>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onPage(data.page - 1)}
            disabled={data.page <= 1 || loading}
            className={buttonClass}
          >
            Previous
          </button>

          <button
            type="button"
            onClick={() => onPage(data.page + 1)}
            disabled={data.page >= pages || loading}
            className={buttonClass}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}
