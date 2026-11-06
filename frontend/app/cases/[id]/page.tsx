import { Suspense } from "react";
import LinksView from "@/components/LinksView";

export default function CaseLinksPage() {
  return (
    <Suspense
      fallback={
        <p className="mt-12 text-center text-sm text-[#777777]">
          Loading linked cases...
        </p>
      }
    >
      <LinksView />
    </Suspense>
  );
}