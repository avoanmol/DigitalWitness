# DigitalWitness demo script

Use synthetic evidence only. Keep mock mode on unless the live API flow has been rehearsed.

## Three-minute walkthrough

**0:00 — Reporter flow**

Sign in with the reporter demo account, create a short synthetic case and attach a sample image. Show upload progress and the receipt. Copy the SHA-256 value and download the receipt JSON.

**0:45 — Investigator workspace**

Switch to the investigator demo account. Filter the case list by verification state, open a case and show the evidence record. Explain that “Verified” means unchanged since anchoring; it does not establish who created the file or whether its contents are accurate.

**1:20 — Integrity and review**

Open a sample evidence record and run the integrity check. Show a pending record as “Pending anchor”, not an alarm. Open the suggested connections page, inspect the shared entity and confidence, then confirm one synthetic suggestion and reject another. Explain that AI output is a lead and a person makes the decision.

**2:10 — Report and custody**

Download the sample PDF report and point to the file hash, anchor fields, verification result, custody events and disclaimer. Open the audit trail as legal or admin and run the audit-chain check.

**2:45 — Limits**

State which screens used mock data and which API routes were live. Do not describe a hash check as proof of authorship or truth. Mention that only a Merkle root and leaf count are anchored; evidence content and identifying details stay off-chain.

## Pre-demo checklist

- [ ] Confirm `NEXT_PUBLIC_USE_MOCK` matches the intended walkthrough and restart Next.js after changing it.
- [ ] Use only synthetic or consented sample evidence.
- [ ] In live mode, log in, create a case and upload one JPG or PDF before presenting.
- [ ] Confirm the evidence worker and local chain are running before showing live anchoring.
- [ ] Confirm the PDF endpoint returns an `application/pdf` response and its custody log matches the case.
- [ ] Keep a mock-mode fallback ready and state clearly when it is used.
