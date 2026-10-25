import { Suspense } from "react";
import CaseView from "@/components/CaseView";

export default function CasePage() {
  return (
    <Suspense fallback={<p className="mt-10 text-center text-sm text-muted">Loading case…</p>}>
      <CaseView />
    </Suspense>
  );
}