import { Suspense } from "react";
import EvidenceView from "@/components/EvidenceView";

export default function EvidencePage() {
  return (
    <Suspense fallback={<p className="mt-10 text-center text-sm text-muted">Loading evidence…</p>}>
      <EvidenceView />
    </Suspense>
  );
}