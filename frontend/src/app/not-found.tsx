import Link from "next/link";

export default function NotFound() {
  return <main className="loading-screen"><div className="empty-state"><div className="empty-icon">?</div><h1>Page not found</h1><p>This link may be old or the record may no longer be available to your role.</p><Link className="button button-primary" href="/cases">Return to cases</Link></div></main>;
}
