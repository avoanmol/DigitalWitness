"use client";

export default function AppError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <main className="loading-screen"><div className="inline-error" role="alert"><strong>This page could not be opened</strong><span>Try again. If the problem continues, sign out and contact the project team.</span><button className="button button-subtle" onClick={reset}>Try again</button></div></main>;
}
