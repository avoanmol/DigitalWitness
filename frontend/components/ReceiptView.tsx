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
    getReceipt(id)
      .then(setReceipt)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load the receipt"));
  }, [id]);

  if (error) return <p className="mt-10 text-center text-sm text-red-600">{error}</p>;
  if (!receipt) return <p className="mt-10 text-center text-sm text-muted">Loading receipt…</p>;
  return <ReceiptCard receipt={receipt} />;
}