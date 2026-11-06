
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getCase } from "@/lib/api";
import type { CaseDetail } from "@/lib/types";
import { formatIST, formatSize } from "@/lib/format";
import { StatusPill } from "@/components/StatusPill";
import VerifyBadge from "@/components/VerifyBadge";

export default function CaseView() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<CaseDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getCase(id)
      .then(setData)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Could not load the case"),
      );
  }, [id]);

  if (error) {
    return <p className="mt-10 text-center text-sm text-red-600">{error}</p>;
  }

  if (!data) {
    return (
      <p className="mt-10 text-center text-sm text-[#777777]">
        Loading case…
      </p>
    );
  }

  const count = (result: string) =>
    data.evidence.filter((e) => e.verification === result).length;

  return (
    <main className="mt-8 pb-16">
      <div className="fade-up">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-[#8A681B]">
          Case record
        </p>

        <div className="mt-3 border-b border-[#D8D5CD] pb-7">
          <p className="text-sm text-[#777777]">{data.caseRef}</p>

          <h1 className="mt-2 max-w-4xl text-3xl font-semibold leading-tight text-[#242424] sm:text-4xl">
            {data.title}
          </h1>

          <div className="mt-4 flex flex-wrap items-center gap-4">
            <StatusPill status={data.status} />
            <span
              className="text-xs text-[#777777]"
              title={`${data.createdAt} (UTC)`}
            >
              Opened {formatIST(data.createdAt)}
            </span>
          </div>

          {data.description && (
            <p className="mt-5 max-w-3xl whitespace-pre-wrap text-sm leading-7 text-[#666666]">
              {data.description}
            </p>
          )}

          <Link
            href={`/cases/${data.id}/links`}
            className="mt-6 inline-flex items-center gap-2 border-b border-[#AD841E] pb-1 text-sm text-[#725719] transition hover:text-[#242424]"
          >
            View related cases <span aria-hidden="true">→</span>
          </Link>
        </div>
      </div>

      <section className="mt-8">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.14em] text-[#888888]">
              Case contents
            </p>
            <h2 className="mt-1 text-xl font-semibold text-[#242424]">
              Evidence records
            </h2>
          </div>

          <p className="text-sm text-[#777777]">
            {data.evidence.length} file
            {data.evidence.length === 1 ? "" : "s"}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4 border-y border-[#D8D5CD] py-5 sm:grid-cols-4">
          <div>
            <p className="text-xs text-[#888888]">Total evidence</p>
            <p className="mt-1 text-2xl font-semibold text-[#242424]">
              {data.evidence.length}
            </p>
          </div>
          <div>
            <p className="text-xs text-[#888888]">Verified</p>
            <p className="mt-1 text-2xl font-semibold text-[#26734D]">
              {count("verified")}
            </p>
          </div>
          <div>
            <p className="text-xs text-[#888888]">Altered</p>
            <p className="mt-1 text-2xl font-semibold text-[#A33B3B]">
              {count("altered")}
            </p>
          </div>
          <div>
            <p className="text-xs text-[#888888]">Pending</p>
            <p className="mt-1 text-2xl font-semibold text-[#8A681B]">
              {count("pending")}
            </p>
          </div>
        </div>

        {data.evidence.length === 0 ? (
          <p className="py-10 text-sm text-[#777777]">
            No evidence has been added to this case yet.
          </p>
        ) : (
          <div className="divide-y divide-[#E5E2DA]">
            {data.evidence.map((e) => (
              <Link
                key={e.id}
                href={`/evidence/${e.id}`}
                className="grid gap-3 py-5 transition-colors hover:bg-[#F8F7F4] sm:grid-cols-[1fr_auto] sm:items-center sm:px-3"
              >
                <div className="min-w-0">
                  <p className="break-words text-sm font-medium text-[#242424]">
                    {e.filename}
                  </p>
                  <p className="mt-1 text-xs text-[#777777]">
                    {e.mimeType} · {formatSize(e.sizeBytes)}
                  </p>
                  <p
                    className="mt-1 text-xs text-[#888888]"
                    title={`${e.uploadedAt} (UTC)`}
                  >
                    Uploaded {formatIST(e.uploadedAt)}
                  </p>
                </div>

                <div className="flex items-center justify-between gap-4 sm:justify-end">
                  <VerifyBadge result={e.verification} compact />
                  <span className="text-sm text-[#AD841E]" aria-hidden="true">
                    →
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
