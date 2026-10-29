"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { FormEvent } from "react";
import { ApiError, isMockMode, registerReporter, signIn } from "@/lib/api";
import { demoUsers } from "@/mocks/fixtures";
import { EmergencyHelp } from "@/components/emergency-help";
import { LogoMark } from "@/components/logo-mark";

export default function LoginPage({ initialMode = "login" }: { initialMode?: "login" | "register" }) {
  const [mode, setMode] = useState<"login" | "register">(initialMode);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const user = mode === "register"
        ? await registerReporter(name.trim(), email.trim(), password)
        : await signIn(email.trim(), password);
      router.replace(user.role === "reporter" ? "/report/new" : "/cases");
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Could not sign in. Please try again.");
    } finally { setBusy(false); }
  }

  function fillDemoAccount(account: string) { setEmail(account); setPassword("demo-access"); }

  return <main className="auth-screen">
    <div className="auth-left"><div className="auth-brand"><LogoMark size={30} reversed /><span>Digital <span className="brand-light">Witness</span></span></div><div className="auth-story"><span className="eyebrow">EVIDENCE, WITH A RECORD</span><h1>Preserve what happened.<br /><em>Show what changed.</em></h1><p>Document what happened, preserve the evidence privately, and give investigators a clear path to review.</p><div className="auth-steps"><div><span>01</span><div><strong>Preserve</strong><small>Your file is encrypted and stored privately</small></div></div><div><span>02</span><div><strong>Verify</strong><small>See whether a file changed after it was saved</small></div></div><div><span>03</span><div><strong>Review</strong><small>Every AI suggestion needs a human decision</small></div></div></div></div><div className="auth-foot">Digital Witness <span>·</span> Document clearly. Move forward. <span>·</span> Synthetic demo data only</div></div>
    <div className="auth-right"><EmergencyHelp /><div className="auth-card">
      <div className="mobile-auth-brand"><LogoMark size={28} /><span>Digital <span className="brand-light">Witness</span></span></div>
      <div className="auth-kicker">DigitalWitness account</div><h2>{mode === "login" ? "Welcome back" : "Create a reporter account"}</h2><p className="auth-intro">{mode === "login" ? "Sign in to continue where you left off." : "Create an account to save your report and track its status."}</p>
      {error && <div className="form-error" role="alert">{error}</div>}
      <form onSubmit={submit} className="form-stack">
        {mode === "register" && <label>Full name<input autoComplete="name" required maxLength={255} value={name} onChange={(event) => setName(event.target.value)} placeholder="Your name" /></label>}
        <label>Email address<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.org" /></label>
        <label>Password<input type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={mode === "register" ? 12 : 1} maxLength={128} required value={password} onChange={(event) => setPassword(event.target.value)} placeholder={mode === "register" ? "At least 12 characters" : "Enter your password"} /></label>
        {mode === "register" && <p className="field-hint">Use 12 or more characters. Public sign-ups are reporters. Investigator, legal, and admin access use separate accounts.</p>}
        {mode === "login" && <p className="reporter-access-hint">Need to make a report? Choose “Create an account” below. It gives you a separate reporter account; your investigator access stays unchanged, and cases do not transfer between accounts.</p>}
        <button className="button button-primary button-wide" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create reporter account"}<span aria-hidden="true">→</span></button>
      </form>
      <div className="auth-switch">{mode === "login" ? "New here?" : "Already have an account?"} <button onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>{mode === "login" ? "Create an account" : "Sign in"}</button></div>
      {isMockMode() && <div className="demo-logins"><div className="demo-title"><span>DEMO ACCOUNTS</span><span>synthetic data</span></div><p>Choose a demo account to explore. Synthetic data only — no real information is used.</p><div className="demo-buttons">{demoUsers.map((user) => <button key={user.role} onClick={() => fillDemoAccount(user.email)}><span>{user.role}</span><b>↗</b></button>)}</div></div>}
      {!isMockMode() && <p className="api-note">If the API cannot be reached, check that it is running at the configured API URL.</p>}
    </div><Link className="auth-help" href="/">Digital Witness <span>·</span> Document clearly. Move forward.</Link></div>
  </main>;
}
