
"use client";

import { usePathname, useRouter } from "next/navigation";

const HIDE_ON = ["/", "/login", "/report/new", "/cases"];

export default function BackButton() {
  const router = useRouter();
  const pathname = usePathname();

  if (HIDE_ON.includes(pathname)) return null;

  function goBack() {
    if (window.history.length > 1) {
      router.back();
    } else {
      router.push("/cases");
    }
  }

  return (
    <div className="mt-5">
      <button
        type="button"
        onClick={goBack}
        aria-label="Go back"
        className="group inline-flex items-center gap-2 border-b border-transparent py-1 text-sm text-[#666666] transition hover:border-[#AD841E] hover:text-[#242424]"
      >
        <span className="transition-transform group-hover:-translate-x-1">
          ←
        </span>
        Back
      </button>
    </div>
  );
}
