
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, USE_MOCK } from "@/lib/api";
import { setSession } from "@/lib/auth";

const field =
  "w-full border border-[#D8D5CD] bg-white px-4 py-3.5 text-sm text-[#242424] outline-none transition placeholder:text-[#999999] focus:border-[#AD841E]";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();

    if (!email || !password) {
      setError("Please enter your email and password.");
      return;
    }

    setError("");
    setBusy(true);

    try {
      const { token, user } = await login(email, password);
      setSession(token, user);
      router.replace(user.role === "reporter" ? "/report/new" : "/cases");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="fade-up mx-auto mt-16 grid w-full max-w-5xl items-start gap-14 md:grid-cols-2 md:gap-20">
      <section className="pt-2">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#AD841E]">
          DigitalWitness
        </p>

        <h1 className="mt-7 text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
          Evidence deserves
          <span className="block text-[#999999]">to be protected.</span>
        </h1>

        <p className="mt-7 max-w-md text-sm leading-8 text-[#777777]">
          Sign in to submit digital evidence, review cases, and access
          preserved evidence records.
        </p>

        <div className="mt-12 border-t border-[#E5E3DD] pt-5">
          <p className="text-xs leading-6 text-[#999999]">
            Preserve the file. Verify its integrity. Keep the record.
          </p>
        </div>
      </section>

      <section className="border-t-2 border-[#242424] pt-7">
        <p className="text-xs uppercase tracking-[0.16em] text-[#AD841E]">
          Account access
        </p>

        <h2 className="mt-3 text-2xl font-semibold">Welcome back</h2>

        <p className="mt-2 text-sm leading-7 text-[#777777]">
          Enter your account details to continue.
        </p>

        <form onSubmit={submit} className="mt-9 space-y-6">
          <div>
            <label
              htmlFor="email"
              className="mb-2 block text-sm font-medium"
            >
              Email address
            </label>

            <input
              id="email"
              className={field}
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-2 block text-sm font-medium"
            >
              Password
            </label>

            <input
              id="password"
              className={field}
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {error && (
            <p role="alert" className="text-sm leading-6 text-red-600">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="flex w-full items-center justify-between bg-[#242424] px-6 py-4 text-sm font-medium text-white transition hover:bg-[#AD841E] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span>{busy ? "Logging in..." : "Log in"}</span>
            <span aria-hidden="true">→</span>
          </button>
        </form>

        {USE_MOCK && (
          <div className="mt-8 border-t border-[#E5E3DD] pt-5">
            <p className="text-xs font-medium text-[#777777]">
              Demo access
            </p>
            <p className="mt-2 text-xs leading-6 text-[#999999]">
              Use reporter@demo.test, investigator@demo.test,
              legal@demo.test, or admin@demo.test with any password.
            </p>
          </div>
        )}
      </section>
    </main>
  );
}
