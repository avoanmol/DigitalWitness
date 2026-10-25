"use client";
import { useEffect, useState } from "react";
import { getEvidenceBlob } from "@/lib/api";

type Props = { evidenceId: string; mimeType: string; filename: string };

export default function EvidencePreview({ evidenceId, mimeType, filename }: Props) {
  const [url, setUrl] = useState<string | null>(null);
  const [text, setText] = useState<string | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "none" | "error">("loading");

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    getEvidenceBlob(evidenceId)
      .then(async (blob) => {
        if (cancelled) return;
        if (!blob) { setState("none"); return; }
        if (mimeType.startsWith("text/") || mimeType === "application/json") {
          setText((await blob.text()).slice(0, 20000));
        } else {
          objectUrl = URL.createObjectURL(blob);
          setUrl(objectUrl);
        }
        setState("ready");
      })
      .catch(() => { if (!cancelled) setState("error"); });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [evidenceId, mimeType]);

  if (state === "loading") return <div className="h-64 animate-pulse rounded-2xl bg-line" />;
  if (state === "error") {
    return <p className="rounded-2xl bg-paper p-6 text-sm text-red-700">Could not load the file.</p>;
  }
  if (state === "none") {
    return (
      <p className="rounded-2xl bg-paper p-6 text-sm text-muted">
        No preview available for this file in mock mode.
      </p>
    );
  }

  // Evidence text is shown as plain text only (React escapes it), never as HTML
  if (text !== null) {
    return (
      <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap break-words rounded-2xl bg-paper p-4 text-sm">
        {text}
      </pre>
    );
  }
  if (url && mimeType.startsWith("image/")) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={url} alt={filename} className="max-h-[60vh] w-full rounded-2xl bg-paper object-contain" />;
  }
  if (url && mimeType === "application/pdf") {
    return <iframe src={url} title={filename} className="h-[60vh] w-full rounded-2xl bg-paper" />;
  }
  if (url && mimeType.startsWith("audio/")) return <audio controls src={url} className="w-full" />;
  if (url && mimeType.startsWith("video/")) {
    return <video controls src={url} className="max-h-[60vh] w-full rounded-2xl" />;
  }
  return <p className="rounded-2xl bg-paper p-6 text-sm text-muted">No preview for this file type.</p>;
}