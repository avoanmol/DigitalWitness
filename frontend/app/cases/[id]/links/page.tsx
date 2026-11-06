import { Suspense } from "react";
import LinksView from "@/components/LinksView";

export default function CaseLinksPage() {
  return (
    <Suspense fallback={<p className="mt-10 text-center text-sm text-muted">Loading linked cases…</p>}>
      <LinksView />
    </Suspense>
  );
}