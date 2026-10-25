"use client";
import { usePathname, useRouter } from "next/navigation";

// Start pages for each role: nothing sensible to go back to
const HIDE_ON = ["/", "/login", "/report/new", "/cases"];

export default function BackButton() {
  const router = useRouter();
  const pathname = usePathname();

  if (HIDE_ON.includes(pathname)) return null;

  function goBack() {
    if (window.history.length > 1) router.back();
    else router.push("/cases"); // opened directly, so no history to go back to
  }

  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={goBack}
        aria-label="Go back"
        className="group inline-flex items-center gap-2 rounded-full border border-ink px-4 py-1.5 text-sm transition hover:bg-ink hover:text-paper"
      >
        <span className="transition group-hover:-translate-x-0.5">←</span>
        Back
      </button>
    </div>
  );
}