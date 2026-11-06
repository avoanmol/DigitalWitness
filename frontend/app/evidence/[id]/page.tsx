import { Suspense } from "react";
import EvidenceView from "@/components/EvidenceView";

export default function EvidencePage() {
  return (
    <Suspense
      fallback={
        <p className="mt-12 text-center text-sm text-[#777777]">
          Loading evidence...
        </p>
      }
    >
      <EvidenceView />
    </Suspense>
  );
}