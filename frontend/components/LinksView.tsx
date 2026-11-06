
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getCaseLinks } from "@/lib/api";
import { useCanReview } from "@/lib/useCanReview";
import type { CaseLink, LinkStatus } from "@/lib/types";
import LinkCard from "@/components/LinkCard";

export default function LinksView() {
  const { id } = useParams<{ id: string }>();
  const canReview = useCanReview();

  const [links, setLinks] = useState<CaseLink[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    getCaseLinks(id)
      .then((result) => {
        if (!cancelled) setLinks(result);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(
            e instanceof Error
              ? e.message
              : "Could not load linked cases",
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  function update(linkId: string, status: LinkStatus) {
    setLinks((current) =>
      current
        ? current.map((link) =>
            link.id === linkId ? { ...link, status } : link,
          )
        : current,
    );
  }

  if (error) {
    return (
      <p className="mt-10 text-center text-sm leading-7 text-red-600">
        {error}
      </p>
    );
  }

  if (!links) {
    return (
      <p className="mt-10 text-center text-sm text-[#777777]">
        Loading linked cases...
      </p>
    );
  }

  const suggested = links.filter((link) => link.status === "suggested");
  const confirmed = links.filter((link) => link.status === "confirmed");
  const rejected = links.filter((link) => link.status === "rejected");

  return (
    <main className="mt-8">
      <header className="max-w-2xl">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-[#AD841E]">
          Case connections
        </p>

        <h1 className="mt-3">Linked cases</h1>

        <p className="mt-4 text-sm leading-8 text-[#777777]">
          Cases may be suggested when they share a phone number, email,
          handle or link. A suggested connection is not confirmed until
          an investigator reviews it.
        </p>
      </header>

      {links.length === 0 && (
        <div className="mt-12 border-y border-[#E5E3DD] py-12">
          <p className="text-base font-medium text-[#242424]">
            No linked cases yet
          </p>
          <p className="mt-2 text-sm leading-7 text-[#777777]">
            Related cases will appear here when shared indicators are found.
          </p>
        </div>
      )}

      {suggested.length > 0 && (
        <section className="mt-12">
          <div className="mb-3 flex flex-wrap items-baseline justify-between gap-3">
            <h2>Needs review</h2>
            <span className="text-sm text-[#777777]">
              {suggested.length} suggestions
            </span>
          </div>

          <div className="divide-y divide-[#E5E3DD]">
            {suggested.map((link) => (
              <LinkCard
                key={link.id}
                link={link}
                canReview={canReview}
                onChange={update}
              />
            ))}
          </div>
        </section>
      )}

      {confirmed.length > 0 && (
        <section className="mt-12">
          <div className="mb-3 flex flex-wrap items-baseline justify-between gap-3">
            <h2>Confirmed connections</h2>
            <span className="text-sm text-[#777777]">
              {confirmed.length} confirmed
            </span>
          </div>

          <div className="divide-y divide-[#E5E3DD]">
            {confirmed.map((link) => (
              <LinkCard
                key={link.id}
                link={link}
                canReview={canReview}
                onChange={update}
              />
            ))}
          </div>
        </section>
      )}

      {rejected.length > 0 && (
        <details className="mt-12 border-t border-[#E5E3DD] pt-6">
          <summary className="cursor-pointer text-sm font-medium text-[#777777] hover:text-[#242424]">
            Rejected suggestions ({rejected.length})
          </summary>

          <div className="mt-4 divide-y divide-[#E5E3DD]">
            {rejected.map((link) => (
              <LinkCard
                key={link.id}
                link={link}
                canReview={canReview}
                onChange={update}
              />
            ))}
          </div>
        </details>
      )}
    </main>
  );
}
