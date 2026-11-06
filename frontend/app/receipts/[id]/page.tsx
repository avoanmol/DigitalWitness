import { Suspense } from "react";
import ReceiptView from "@/components/ReceiptView";

export default function ReceiptPage() {
  return (
    <Suspense
      fallback={
        <p className="mt-12 text-center text-sm text-[#777777]">
          Loading receipt...
        </p>
      }
    >
      <ReceiptView />
    </Suspense>
  );
}