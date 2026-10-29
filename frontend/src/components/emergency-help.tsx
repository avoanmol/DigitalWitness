"use client";

import { useState } from "react";

type SafetyChoice = "urgent" | "continue" | null;

export function EmergencyHelp() {
  const [choice, setChoice] = useState<SafetyChoice>(null);

  return <section className="emergency-check" aria-labelledby="emergency-question">
    <div className="emergency-check-copy">
      <span className="eyebrow">SAFETY FIRST</span>
      <h2 id="emergency-question">Are you or someone else in immediate danger right now?</h2>
      <p>You do not need an account, an upload, or an AI review to ask for emergency help.</p>
    </div>
    <div className="emergency-check-actions">
      <button type="button" className="button button-danger" aria-pressed={choice === "urgent"} onClick={() => setChoice("urgent")}>Yes, I need urgent help</button>
      <button type="button" className="text-button" aria-pressed={choice === "continue"} onClick={() => setChoice("continue")}>No, I can continue</button>
    </div>
    {choice === "urgent" && <div className="emergency-callout" role="alert">
      <strong>If you are in India, call 112 now for emergency assistance.</strong>
      <a className="button button-danger" href="tel:112">Call 112</a>
      <a href="https://112.gov.in/" target="_blank" rel="noopener noreferrer">Official 112 emergency information ↗</a>
      <small>DigitalWitness is not an emergency service. Do not wait for this app if you need help now.</small>
    </div>}
    {choice === "continue" && <p className="emergency-continue" role="status">Continue only when it feels safe. Your answer is not saved.</p>}
  </section>;
}
