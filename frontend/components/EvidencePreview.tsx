"use client";

import { useEffect, useState } from "react";
import { getEvidenceBlob } from "@/lib/api";

type Props = {
  evidenceId: string;
  mimeType: string;
  filename: string;
};

export default function EvidencePreview({
  evidenceId,
  mimeType,
  filename,
}: Props) {
  const [url, setUrl] = useState<string | null>(null);
  const [text, setText] = useState<string | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "none" | "error">(
    "loading"
  );

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;

    setUrl(null);
    setText(null);
    setState("loading");

    getEvidenceBlob(evidenceId)
      .then(async (blob) => {
        if (cancelled) return;

        if (!blob) {
          setState("none");
          return;
        }

        if (
          mimeType.startsWith("text/") ||
          mimeType === "application/json"
        ) {
          const content = await blob.text();

          if (cancelled) return;

          setText(content.slice(0, 20000));
        } else {
          objectUrl = URL.createObjectURL(blob);
          setUrl(objectUrl);
        }

        if (!cancelled) setState("ready");
      })
      .catch(() => {
        if (!cancelled) setState("error");
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [evidenceId, mimeType]);

  if (state === "loading") {
    return (
      <div
        role="status"
        aria-label="Loading evidence preview"
        className="flex min-h-64 items-center justify-center border border-[#E5E2DA] bg-[#F7F6F2]"
      >
        <div className="flex items-center gap-3 text-sm text-[#77736B]">
          <span className="h-2 w-2 animate-pulse bg-[#AD841E]" />
          Loading original file...
        </div>
      </div>
    );
  }

  if (state === "error") {
    return (
      <p className="border border-red-200 bg-red-50 p-6 text-sm text-red-700">
        Could not load the file.
      </p>
    );
  }

  if (state === "none") {
    return (
      <p className="border border-[#E5E2DA] bg-[#F7F6F2] p-6 text-sm text-[#77736B]">
        No preview available for this file in mock mode.
      </p>
    );
  }

  // Evidence text is displayed as plain text only, never as HTML.
  if (text !== null) {
    return (
      <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap break-words border border-[#E5E2DA] bg-[#F7F6F2] p-5 text-sm leading-6 text-[#242424]">
        {text}
      </pre>
    );
  }

  if (url && mimeType.startsWith("image/")) {
    // eslint-disable-next-line @next/next/no-img-element
    return (
      <img
        src={url}
        alt={filename}
        className="max-h-[65vh] w-full bg-[#F7F6F2] object-contain"
      />
    );
  }

  if (url && mimeType === "application/pdf") {
    return (
      <iframe
        src={url}
        title={filename}
        className="h-[65vh] w-full border border-[#E5E2DA] bg-white"
      />
    );
  }

  if (url && mimeType.startsWith("audio/")) {
    return <audio controls src={url} className="w-full" />;
  }

  if (url && mimeType.startsWith("video/")) {
    return (
      <video
        controls
        src={url}
        className="max-h-[65vh] w-full bg-black"
      />
    );
  }

  return (
    <p className="border border-[#E5E2DA] bg-[#F7F6F2] p-6 text-sm text-[#77736B]">
      No preview for this file type.
    </p>
  );
}