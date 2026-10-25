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
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load the case"));
  }, [id]);

  if (error) return <p className="mt-10 text-center text-sm text-red-600">{error}</p>;
  if (!data) return <p className="mt-10 text-center text-sm text-muted">Loading case…</p>;

  const count = (r: string) => data.evidence.filter((e) => e.verification === r).length;

  return (
    <main className="mt-6">
      

      <div className="fade-up mt-4 grid gap-4 lg:grid-cols-5">
        <section className="lg:col-span-3">
          <p className="text-sm text-muted">{data.caseRef}</p>
          <h1 className="mt-1 text-3xl font-semibold leading-tight sm:text-4xl">{data.title}</h1>
          <div className="mt-3 flex items-center gap-3">
            <StatusPill status={data.status} />
            <span className="text-xs text-muted" title={`${data.createdAt} (UTC)`}>
              Opened {formatIST(data.createdAt)}
            </span>
          </div>
          {data.description && (
            <p className="mt-5 max-w-xl whitespace-pre-wrap text-sm text-muted">{data.description}</p>
          )}
        </section>

        <section className="grid grid-cols-2 gap-3 lg:col-span-2">
          <div className="rounded-3xl bg-ink p-5 text-paper">
            <p className="text-3xl font-semibold">{data.evidence.length}</p>
            <p className="mt-1 text-xs text-white/60">evidence files</p>
          </div>
          <div className="rounded-3xl bg-card p-5">
            <p className="text-3xl font-semibold">{count("altered")}</p>
            <p className="mt-1 text-xs text-muted">
              altered · {count("verified")} verified · {count("pending")} pending
            </p>
          </div>
        </section>
      </div>

      <h2 className="mt-10 text-xl font-semibold">Evidence</h2>
      <div className="mt-3 space-y-2">
        {data.evidence.length === 0 && (
          <p className="rounded-3xl bg-card p-6 text-sm text-muted">No evidence uploaded yet.</p>
        )}
        {data.evidence.map((e) => (
          <Link
            key={e.id}
            href={`/evidence/${e.id}`}
            className="flex items-center justify-between gap-3 rounded-2xl bg-card p-4 transition hover:bg-line/60"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{e.filename}</p>
              <p className="text-xs text-muted" title={`${e.uploadedAt} (UTC)`}>
                {formatSize(e.sizeBytes)} · {formatIST(e.uploadedAt)}
              </p>
            </div>
            <VerifyBadge result={e.verification} compact />
          </Link>
        ))}
      </div>
    </main>
  );
}