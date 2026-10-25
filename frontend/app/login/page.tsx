"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, USE_MOCK } from "@/lib/api";
import { setSession } from "@/lib/auth";

const field =
  "w-full rounded-2xl border border-line bg-paper p-3 outline-none transition focus:border-ink";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) { setError("Please enter your email and password."); return; }
    setError(""); setBusy(true);
    try {
      const { token, user } = await login(email, password);
      setSession(token, user);
      router.replace(user.role === "reporter" ? "/report/new" : "/cases");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally { setBusy(false); }
  }

  return (
    <main className="fade-up mx-auto mt-12 max-w-sm">
      <div className="rounded-3xl bg-card p-6">
        <h1 className="text-2xl font-semibold">Welcome back</h1>
        <p className="mt-1 text-sm text-muted">Log in to save or review evidence.</p>

        <form onSubmit={submit} className="mt-6 space-y-3">
          <input className={field} type="email" placeholder="Email" value={email}
            onChange={(e) => setEmail(e.target.value)} />
          <input className={field} type="password" placeholder="Password" value={password}
            onChange={(e) => setPassword(e.target.value)} />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="submit" disabled={busy}
            className="w-full rounded-full bg-ink p-3 text-paper transition disabled:opacity-50">
            {busy ? "Logging in…" : "Log in"}
          </button>
        </form>

        {USE_MOCK && (
          <p className="mt-4 text-xs text-muted">
            Mock mode: use reporter@, investigator@, legal@ or admin@demo.test with any password.
          </p>
        )}
      </div>
    </main>
  );
}