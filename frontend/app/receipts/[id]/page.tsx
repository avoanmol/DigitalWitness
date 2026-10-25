import { Suspense } from "react";
import ReceiptView from "@/components/ReceiptView";

export default function ReceiptPage() {
  return (
    <Suspense
      fallback={<p className="mt-10 text-center text-sm text-muted">Loading receipt…</p>}
    >
      <ReceiptView />
    </Suspense>
  );
}