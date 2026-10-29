# Reporter workflow

DigitalWitness helps a reporter preserve evidence and prepare a draft. It does not provide emergency response, verify a person’s identity, decide whether a crime occurred, or file a complaint.

## 1. Check immediate safety

The safety question appears before sign-in and again at report intake. If the reporter or someone else is in immediate danger in India, choose **Yes, I need urgent help** and call **112**. Do not wait for an upload or AI review. The Government of India describes 112 as its pan-India emergency response number: [112.gov.in](https://112.gov.in/).

The answer to the safety question is not saved.

## 2. Create a reporter account

Choose **Create an account** on the sign-in page. Public sign-ups receive the reporter role. A reporter account is separate from investigator, legal, or admin accounts, and cases stay with the account that created them.

## 3. Start a case and preserve evidence

Use a short case title and, if useful, a brief summary. The title and summary are saved with the case and may be visible to authorized reviewers. Do not put Aadhaar numbers, passwords, a full home address, or unnecessary identifying details there.

Upload the original evidence file. DigitalWitness stores it in encrypted private object storage and records its SHA-256 fingerprint. The blockchain receives only a batch fingerprint; it does not receive the file or the reporter’s statement. Keep the original file and download the receipt.

## 4. Review the file and AI notes

Open the original evidence and compare it with each AI source excerpt. AI notes are suggestions, not proof of authenticity, intent, or a crime. A matching fingerprint shows only that the saved file matches its recorded fingerprint; it cannot prove the screenshot, audio, or video was genuine when created.

For the complaint draft, the reporter can leave a correction or context note beside an AI suggestion, or omit that suggestion from the draft. This affects only that download; it does not edit the saved AI note. An investigator’s review is recorded separately.

## 5. Prepare and review a complaint draft

The reporter can add the incident date/time, platform, account or content link, and a statement in their own words. The narrative is used to make the download and is not saved in the case database or audit log. Aadhaar, passwords, and a full home address are not requested.

State, district, and police-station fields appear only for the local-police option and are optional. DigitalWitness does not look up, choose, or contact a police station. The packet lists the case evidence and selected AI notes, clearly marked as suggestions. The reporter must review the complete draft before downloading it.

## 6. Choose whether to report outside the app

The reporter may open the official [National Cyber Crime Reporting Portal](https://www.cybercrime.gov.in/) or take the draft and original evidence to local police. DigitalWitness never submits the packet. The official portal may request identity or contact details depending on the route selected; its [FAQ](https://www.cybercrime.gov.in/webform/FAQ.aspx) describes the available reporting routes and their requirements.

After filing, the reporter may optionally save the external complaint reference in DigitalWitness. It is encrypted at rest, retrievable only through the owning reporter account, and can be removed. The reference itself is not written to the blockchain or the audit log.

## Role boundaries

- **Reporter:** creates and owns cases, uploads evidence, reviews AI notes for their draft, prepares a packet, and chooses whether to report externally.
- **Investigator:** reviews evidence and AI suggestions and records human review decisions.
- **Legal:** reviews case material and reports according to assigned permissions.
- **Admin:** manages accounts and workspace settings. Admin access does not turn an account into a reporter account.

For local synthetic role accounts, see [demo-accounts.md](demo-accounts.md). Never use demo accounts for real incidents.
