
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getReceipt } from "@/lib/api";
import type { Receipt } from "@/lib/types";
import ReceiptCard from "@/components/ReceiptCard";

export default function ReceiptView() {
  const { id } = useParams<{ id: string }>();

  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    getReceipt(id)
      .then((result) => {
        if (!cancelled) setReceipt(result);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(
            e instanceof Error
              ? e.message
              : "Could not load the receipt",
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) {
    return (
      <main className="mx-auto mt-16 max-w-2xl">
        <p className="text-xs font-semibold uppercase tracking-[0.15em] text-red-600">
          Receipt unavailable
        </p>
        <h1 className="mt-4 text-2xl">Could not load your receipt</h1>
        <p className="mt-3 text-sm leading-8 text-[#777777]">
          {error}
        </p>
      </main>
    );
  }

  if (!receipt) {
    return (
      <main className="mx-auto mt-16 max-w-2xl" aria-live="polite">
        <div className="h-3 w-28 animate-pulse bg-[#E5E3DD]" />
        <div className="mt-5 h-9 w-72 max-w-full animate-pulse bg-[#E5E3DD]" />
        <div className="mt-4 h-4 w-full max-w-md animate-pulse bg-[#F0EFEB]" />
        <div className="mt-10 space-y-5 border-y border-[#E5E3DD] py-8">
          <div className="h-4 w-40 animate-pulse bg-[#F0EFEB]" />
          <div className="h-4 w-64 max-w-full animate-pulse bg-[#F0EFEB]" />
          <div className="h-4 w-52 max-w-full animate-pulse bg-[#F0EFEB]" />
        </div>
      </main>
    );
  }

  return <ReceiptCard receipt={receipt} />;
}
