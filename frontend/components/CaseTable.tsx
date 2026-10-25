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

const th = "px-3 py-2 font-medium";
const td = "px-3 py-3 align-middle";

export default function CaseTable({ data, loading, error, onPage }: Props) {
  if (error) {
    return <div className="rounded-3xl bg-card p-8 text-center text-sm text-red-700">{error}</div>;
  }

  if (loading && !data) {
    return (
      <div className="space-y-2 rounded-3xl bg-card p-4" aria-busy="true">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-10 animate-pulse rounded-2xl bg-line" />
        ))}
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="rounded-3xl bg-card p-10 text-center">
        <p className="text-lg font-semibold">No cases found</p>
        <p className="mt-1 text-sm text-muted">Try changing or clearing the filters.</p>
      </div>
    );
  }

  const pages = Math.max(1, Math.ceil(data.total / data.pageSize));

  return (
    <div className="fade-up">
      <div className={`overflow-x-auto rounded-3xl bg-card p-2 transition ${loading ? "opacity-60" : ""}`}>
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="text-xs text-muted">
            <tr>
              <th className={th}>Case</th>
              <th className={th}>Title</th>
              <th className={th}>Status</th>
              <th className={th}>Severity</th>
              <th className={th}>Threat types</th>
              <th className={th}>Verification</th>
              <th className={th}>Files</th>
              <th className={th}>Created</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((c) => (
              <tr key={c.id} className="border-t border-line transition hover:bg-paper">
                <td className={`${td} font-medium`}>
                  <Link href={`/cases/${c.id}`} className="hover:underline">{c.caseRef}</Link>
                </td>
                <td className={td}>
                  <Link href={`/cases/${c.id}`} className="hover:underline">{c.title}</Link>
                </td>
                <td className={td}><StatusPill status={c.status} /></td>
                <td className={td}>
                  {c.topSeverity ? <SeverityPill severity={c.topSeverity} /> : <span className="text-muted">—</span>}
                </td>
                <td className={`${td} text-muted`}>
                  {c.threatClasses.length ? c.threatClasses.map((t) => threatLabels[t]).join(", ") : "—"}
                </td>
                <td className={td}><VerifyBadge result={c.verification} compact /></td>
                <td className={td}>{c.evidenceCount}</td>
                <td className={`${td} text-muted`} title={`${c.createdAt} (UTC)`}>
                  {formatIST(c.createdAt)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-3 flex items-center justify-between text-sm text-muted">
        <span>Page {data.page} of {pages} · {data.total} cases</span>
        <div className="flex gap-2">
          <button
            onClick={() => onPage(data.page - 1)}
            disabled={data.page <= 1}
            className="rounded-full border border-ink px-4 py-1.5 text-ink transition hover:bg-ink hover:text-paper disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-ink"
          >
            Previous
          </button>
          <button
            onClick={() => onPage(data.page + 1)}
            disabled={data.page >= pages}
            className="rounded-full border border-ink px-4 py-1.5 text-ink transition hover:bg-ink hover:text-paper disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-ink"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}