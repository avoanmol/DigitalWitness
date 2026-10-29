"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { EmergencyHelp } from "@/components/emergency-help";
import { LogoMark } from "@/components/logo-mark";
import { getSessionUser } from "@/lib/session";

const processSteps = [
  {
    number: "01",
    title: "Start a private record",
    description: "Add a short case label and the context you know. You can leave uncertain details blank.",
  },
  {
    number: "02",
    title: "Preserve the original file",
    description: "Upload a screenshot, chat export, document, audio, or video. The saved original is access-controlled.",
  },
  {
    number: "03",
    title: "Review before you act",
    description: "Check integrity details and any AI-assisted notes. Prepare a complaint draft only when you are ready.",
  },
];

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const user = getSessionUser();
    if (user) router.replace(user.role === "reporter" ? "/report/new" : "/cases");
  }, [router]);

  return (
    <main className="public-site">
      <div className="public-shell">
        <header className="public-header">
          <Link className="public-brand" href="/" aria-label="DigitalWitness home">
            <LogoMark size={30} reversed />
            <span>Digital<span>Witness</span></span>
          </Link>
          <nav className="public-nav" aria-label="Main navigation">
            <a href="#workflow">How it works</a>
            <a href="#privacy">Privacy and limits</a>
            <a href="#safety">Urgent help</a>
          </nav>
          <div className="public-actions">
            <Link className="public-signin" href="/login">Sign in</Link>
            <Link className="button button-primary public-cta" href="/register">Get documenting <span aria-hidden="true">→</span></Link>
          </div>
        </header>

        <div className="public-content">
          <section className="public-safety" id="safety" aria-label="Urgent safety help">
            <EmergencyHelp />
          </section>

          <section className="public-hero" aria-labelledby="home-title">
            <div className="public-hero-copy">
              <span className="public-eyebrow"><span /> PRIVATE EVIDENCE WORKSPACE</span>
              <h1 id="home-title">Make a record.<br /><em>Keep control.</em></h1>
              <p className="public-lead">
                Preserve digital evidence, review AI-assisted notes, and prepare a complaint draft when you are ready. You stay in control of what you share and where you report.
              </p>
              <div className="public-hero-actions">
                <Link className="button button-primary public-start" href="/register">Get documenting <span aria-hidden="true">→</span></Link>
                <Link className="public-login-link" href="/login">Already have an account? Sign in</Link>
              </div>
              <p className="public-no-submit"><span aria-hidden="true">↗</span> Nothing is sent to police or a portal from this app.</p>
            </div>

            <div className="record-visual" aria-label="How DigitalWitness handles an evidence file">
              <div className="record-visual-top">
                <div><span className="public-eyebrow">THE EVIDENCE RECORD</span><strong>From original file to review</strong></div>
                <span className="record-visual-index">DW / 01</span>
              </div>
              <div className="record-flow">
                <div className="record-stage">
                  <span className="record-stage-icon file-stage" aria-hidden="true">01</span>
                  <div><strong>Original file</strong><small>Kept in private storage</small></div>
                  <span className="record-stage-state">PRIVATE</span>
                </div>
                <div className="record-flow-line" aria-hidden="true" />
                <div className="record-stage">
                  <span className="record-stage-icon hash-stage" aria-hidden="true">02</span>
                  <div><strong>File fingerprint</strong><small>SHA-256 recorded with a receipt</small></div>
                  <span className="record-stage-state">CHECKABLE</span>
                </div>
                <div className="record-flow-line" aria-hidden="true" />
                <div className="record-stage">
                  <span className="record-stage-icon chain-stage" aria-hidden="true">03</span>
                  <div><strong>Batch anchor</strong><small>Only a batch fingerprint goes on-chain</small></div>
                  <span className="record-stage-state">HASH ONLY</span>
                </div>
              </div>
              <div className="record-visual-note"><span aria-hidden="true">i</span> A matching fingerprint shows a file has not changed since it was recorded. It does not prove the file was genuine before upload.</div>
            </div>
          </section>

          <section className="public-section workflow-section" id="workflow" aria-labelledby="workflow-title">
            <div className="section-heading">
              <div><span className="public-eyebrow">A SIMPLE, REVIEWABLE PROCESS</span><h2 id="workflow-title">Start with what you have.</h2></div>
              <p>No need to know the right category or have every detail ready. You can add context as you go.</p>
            </div>
            <div className="workflow-grid">
              {processSteps.map((step) => (
                <article className="workflow-card" key={step.number}>
                  <span className="workflow-number">{step.number}</span>
                  <h3>{step.title}</h3>
                  <p>{step.description}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="public-section trust-section" id="privacy" aria-labelledby="privacy-title">
            <div className="trust-copy">
              <span className="public-eyebrow">PLAIN ABOUT PRIVACY AND LIMITS</span>
              <h2 id="privacy-title">A record can help.<br /><em>It cannot decide what happened.</em></h2>
              <p>DigitalWitness helps organize and preserve material. It is not an emergency service, a police authority, or a verdict on whether a crime occurred.</p>
              <Link className="button button-subtle trust-link" href="/register">Start a private record <span aria-hidden="true">→</span></Link>
            </div>
            <div className="trust-list">
              <article><span className="trust-mark">01</span><div><h3>Your files stay off-chain</h3><p>Files and personal details are stored off-chain. Only a batch fingerprint is anchored publicly.</p></div></article>
              <article><span className="trust-mark">02</span><div><h3>AI notes are suggestions</h3><p>They can miss context or be wrong. Review the source material and add your own correction.</p></div></article>
              <article><span className="trust-mark">03</span><div><h3>You choose the next step</h3><p>Review and download a draft, then decide whether to use an official reporting channel yourself.</p></div></article>
            </div>
          </section>

          <section className="public-bottom-cta" aria-label="Start documenting">
            <div><span className="public-eyebrow">WHEN YOU FEEL READY</span><h2>Begin with one file.</h2><p>You can continue in your own time. No complaint is filed automatically.</p></div>
            <Link className="button button-primary public-start" href="/register">Get documenting <span aria-hidden="true">→</span></Link>
          </section>
        </div>

        <footer className="public-footer">
          <Link className="public-brand" href="/" aria-label="DigitalWitness home"><LogoMark size={24} reversed /><span>Digital<span>Witness</span></span></Link>
          <p>DigitalWitness preserves a record and supports complaint preparation. It does not prove that content is true or submit a complaint.</p>
          <span className="public-footer-meta">© DigitalWitness · Your evidence, your decision</span>
        </footer>
      </div>
    </main>
  );
}
