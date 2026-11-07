"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { EmergencyHelp } from "@/components/emergency-help";
import { LogoMark } from "@/components/logo-mark";
import { getSessionUser } from "@/lib/session";

const steps = [
  { number: "01", title: "Document", body: "Write down what happened and add the files you already have." },
  { number: "02", title: "Preserve", body: "Keep the original in private storage and record its file fingerprint." },
  { number: "03", title: "Review", body: "Check the record, consider AI notes, and decide what you want to do next." },
];

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    const user = getSessionUser();
    if (user) router.replace(user.role === "reporter" ? "/report/new" : "/cases");
  }, [router]);

  return <main className="dw-public-page">
    <div className="dw-public-shell">
      <header className="dw-public-header">
        <Link className="dw-public-brand" href="/" aria-label="DigitalWitness home"><LogoMark size={30} /><span>DigitalWitness</span></Link>
        <nav className="dw-public-nav" aria-label="Main navigation"><a href="#how-it-works">How it works</a><a href="#what-it-does">What it does</a><a href="#limits">Limits</a></nav>
        <div className="dw-public-actions"><Link className="dw-public-signin" href="/login">Sign in</Link><Link className="button button-primary" href="/register">Get documenting <span aria-hidden="true">→</span></Link></div>
      </header>

      <div className="dw-home-safety"><EmergencyHelp /></div>

      <section className="pr-home-hero" aria-labelledby="home-title">
        <div className="pr-hero-art" aria-hidden="true"><div className="fingerprint-rings"><i /><i /><i /><i /><i /><i /><i /></div><span className="fingerprint-point point-one" /><span className="fingerprint-point point-two" /><span className="fingerprint-point point-three" /></div>
        <p className="pr-eyebrow"><span /> DIGITAL EVIDENCE, CLEARLY RECORDED</p>
        <h1 id="home-title">Preserve evidence.<br /><em>Establish integrity.</em><br />Connect the dots.</h1>
        <p className="pr-home-lead">Document online incidents, preserve original files, and organize reviewable evidence in one private workspace.</p>
        <div className="pr-home-actions"><Link className="button button-primary pr-home-cta" href="/register">Get documenting <span aria-hidden="true">→</span></Link><Link className="button button-outline" href="/login">Sign in to your workspace</Link></div>
        <div className="pr-tagline"><span /> Preserve <b>·</b> Review <b>·</b> Prepare <span /></div>
        <p className="pr-hero-disclaimer">DigitalWitness does not decide whether an incident occurred or submit a complaint for you.</p>
      </section>

      <section className="pr-home-section pr-purpose" id="what-it-does">
        <div><p className="pr-eyebrow">WHY DIGITALWITNESS</p><h2>Evidence deserves more than a screenshot folder.</h2></div>
        <div className="pr-purpose-copy"><p>Online incidents can leave screenshots, messages, recordings, and documents scattered across devices. DigitalWitness helps keep a clear record of what was submitted and when.</p><p>Original files remain private. A fingerprint can help check whether a saved file changed later, while AI notes and possible case links remain suggestions for human review.</p></div>
      </section>

      <section className="pr-home-section" id="how-it-works">
        <div className="pr-section-heading"><div><p className="pr-eyebrow">THE PROCESS</p><h2>From documentation to review.</h2></div><p>Start with what you have. You can add context as it becomes available.</p></div>
        <div className="pr-step-grid">{steps.map((step) => <article className="pr-step-card" key={step.number}><span>{step.number}</span><h3>{step.title}</h3><p>{step.body}</p></article>)}</div>
      </section>

      <section className="pr-home-section pr-limits" id="limits">
        <div><p className="pr-eyebrow">IMPORTANT TO UNDERSTAND</p><h2>A file record is useful.<br /><em>It is not a verdict.</em></h2><p>DigitalWitness supports documentation and review. It cannot independently prove who created a file, whether its contents are true, or who controls an online account.</p><Link className="button button-primary" href="/register">Start a private record <span aria-hidden="true">→</span></Link></div>
        <div className="pr-limit-list"><article><span>01</span><div><h3>Files stay off-chain</h3><p>Only a batch fingerprint is anchored. Your files and personal details are not published on-chain.</p></div></article><article><span>02</span><div><h3>AI gives review notes</h3><p>Automated analysis can miss context or be wrong. A person should check the original material.</p></div></article><article><span>03</span><div><h3>You choose where to report</h3><p>Prepare a draft, review it, and decide whether to continue through an official reporting channel.</p></div></article></div>
      </section>

      <footer className="dw-public-footer"><Link className="dw-public-brand" href="/"><LogoMark size={25} /><span>DigitalWitness</span></Link><p>Preserving a record. Keeping the next step in your hands.</p><span>© DigitalWitness</span></footer>
    </div>
  </main>;
}
