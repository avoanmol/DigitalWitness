import type {
  CaseDetail, CaseFilters, CaseSummary, EvidenceItem, Proof, Receipt,
  Severity, ThreatClass, User, Verification, VerifyResult,
} from "@/lib/types";

// ---------- Day 1: users and receipts ----------
const demo = (email: string, fullName: string, role: User["role"], id: string): User => ({
  id, email, fullName, role,
});

export const demoUsers: Record<string, User> = {
  "reporter@demo.test": demo("reporter@demo.test", "Demo Reporter", "reporter", "u1"),
  "investigator@demo.test": demo("investigator@demo.test", "Demo Investigator", "investigator", "u2"),
  "legal@demo.test": demo("legal@demo.test", "Demo Legal", "legal", "u3"),
  "admin@demo.test": demo("admin@demo.test", "Demo Admin", "admin", "u4"),
};

const FAKE_HASH = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08";

// Receipts created during this browser session (mock mode only)
export const mockStore = new Map<string, Receipt>();

export function makeMockReceipt(file: File): Receipt {
  const id = `mock-${Date.now()}`;
  return {
    receiptId: id,
    caseRef: "DW-2026-0001",
    evidenceId: id,
    filename: file.name,
    sizeBytes: file.size,
    sha256: FAKE_HASH,
    uploadedAt: new Date().toISOString(),
    status: "stored",
    signature: "mock-signature",
  };
}

export const fallbackReceipt: Receipt = {
  receiptId: "mock-demo",
  caseRef: "DW-2026-0001",
  evidenceId: "mock-demo",
  filename: "chat-screenshot.png",
  sizeBytes: 182344,
  sha256: FAKE_HASH,
  uploadedAt: "2026-10-23T09:15:00Z",
  status: "stored",
  signature: "mock-signature",
};

// ---------- Day 2: cases and evidence (all synthetic) ----------
type MockCase = CaseDetail & { threats: { cls: ThreatClass; severity: Severity }[] };

const hash = (n: number) => n.toString(16).padStart(2, "0").repeat(32);

function ev(
  n: number, caseId: string, filename: string, mimeType: string,
  sizeBytes: number, uploadedAt: string, verification: VerifyResult
): EvidenceItem {
  return {
    id: `e${n}`, caseId, filename, mimeType, sizeBytes, sha256: hash(n), uploadedAt,
    status: verification === "pending" ? "stored" : "anchored",
    analysisStatus: "done", verification,
  };
}

export const mockCases: MockCase[] = [
  {
    id: "c1", caseRef: "DW-2026-0001", title: "Blackmail messages on WhatsApp",
    description: "Someone is demanding money and threatening to share private photos.",
    status: "under_review", createdAt: "2026-10-18T09:15:00Z",
    threats: [{ cls: "extortion_blackmail", severity: "high" }],
    evidence: [
      ev(1, "c1", "chat-screenshot.png", "image/png", 182344, "2026-10-18T09:15:00Z", "verified"),
      ev(2, "c1", "chat-export.txt", "text/plain", 4210, "2026-10-18T09:20:00Z", "verified"),
    ],
  },
  {
    id: "c2", caseRef: "DW-2026-0002", title: "Scam calls from an unknown number",
    description: "Caller pretended to be from a bank and asked for an OTP.",
    status: "open", createdAt: "2026-10-19T11:40:00Z",
    threats: [{ cls: "fraud_scam", severity: "medium" }],
    evidence: [ev(3, "c2", "call-log.png", "image/png", 90210, "2026-10-19T11:40:00Z", "pending")],
  },
  {
    id: "c3", caseRef: "DW-2026-0003", title: "Threats in Instagram DMs",
    description: "Repeated direct messages threatening to hurt the reporter.",
    status: "under_review", createdAt: "2026-10-20T08:05:00Z",
    threats: [{ cls: "violence_threat", severity: "critical" }, { cls: "harassment_stalking", severity: "medium" }],
    evidence: [
      ev(4, "c3", "dm-part-1.png", "image/png", 150120, "2026-10-20T08:05:00Z", "verified"),
      ev(5, "c3", "dm-part-2.png", "image/png", 143880, "2026-10-20T08:07:00Z", "altered"),
    ],
  },
  {
    id: "c4", caseRef: "DW-2026-0004", title: "Fake job offer asking for a fee",
    description: "A recruiter asked for a registration fee before an interview.",
    status: "closed", createdAt: "2026-10-12T14:30:00Z",
    threats: [{ cls: "fraud_scam", severity: "medium" }],
    evidence: [ev(6, "c4", "offer-letter.pdf", "application/pdf", 320400, "2026-10-12T14:30:00Z", "verified")],
  },
  {
    id: "c5", caseRef: "DW-2026-0005", title: "Harassing comments on posts",
    description: "Same account keeps posting insulting comments under every photo.",
    status: "open", createdAt: "2026-10-21T16:10:00Z",
    threats: [{ cls: "harassment_stalking", severity: "low" }],
    evidence: [ev(7, "c5", "comments.png", "image/png", 120500, "2026-10-21T16:10:00Z", "pending")],
  },
  {
    id: "c6", caseRef: "DW-2026-0006", title: "Threatening voice note",
    description: "A voice note saying the reporter would be followed home.",
    status: "open", createdAt: "2026-10-22T07:50:00Z",
    threats: [{ cls: "violence_threat", severity: "high" }],
    evidence: [ev(8, "c6", "voice-note.m4a", "audio/mp4", 880000, "2026-10-22T07:50:00Z", "verified")],
  },
  {
    id: "c7", caseRef: "DW-2026-0007", title: "Abusive messages in a group chat",
    description: "A group chat export with abuse aimed at a community.",
    status: "under_review", createdAt: "2026-10-22T18:25:00Z",
    threats: [{ cls: "hate_speech", severity: "medium" }],
    evidence: [ev(9, "c7", "group-chat.txt", "text/plain", 9800, "2026-10-22T18:25:00Z", "verified")],
  },
  {
    id: "c8", caseRef: "DW-2026-0008", title: "Lottery scam email",
    description: "Email claiming a prize if the reporter pays a processing fee.",
    status: "open", createdAt: "2026-10-23T10:00:00Z",
    threats: [{ cls: "fraud_scam", severity: "low" }],
    evidence: [ev(10, "c8", "email.pdf", "application/pdf", 210000, "2026-10-23T10:00:00Z", "error")],
  },
];

const rank: Severity[] = ["low", "medium", "high", "critical"];

function toSummary(c: MockCase): CaseSummary {
  const top = c.threats.reduce<Severity | null>(
    (best, t) => (!best || rank.indexOf(t.severity) > rank.indexOf(best) ? t.severity : best),
    null
  );
  const results = c.evidence.map((e) => e.verification);
  const verification: VerifyResult | null = results.includes("altered")
    ? "altered"
    : results.includes("error")
    ? "error"
    : results.includes("pending")
    ? "pending"
    : results.length > 0 && results.every((r) => r === "verified")
    ? "verified"
    : null;
  return {
    id: c.id, caseRef: c.caseRef, title: c.title, status: c.status, createdAt: c.createdAt,
    evidenceCount: c.evidence.length, topSeverity: top,
    threatClasses: Array.from(new Set(c.threats.map((t) => t.cls))),
    verification,
  };
}

export function mockCaseSummaries(f: CaseFilters): CaseSummary[] {
  const q = f.q.trim().toLowerCase();
  return mockCases.map(toSummary).filter(
    (c) =>
      (!q || c.caseRef.toLowerCase().includes(q) || c.title.toLowerCase().includes(q)) &&
      (!f.status || c.status === f.status) &&
      (!f.severity || c.topSeverity === f.severity) &&
      (!f.threatClass || c.threatClasses.includes(f.threatClass)) &&
      (!f.verification || c.verification === f.verification) &&
      (!f.from || c.createdAt.slice(0, 10) >= f.from) &&
      (!f.to || c.createdAt.slice(0, 10) <= f.to)
  );
}

export function findMockEvidence(id: string): EvidenceItem | undefined {
  for (const c of mockCases) {
    const found = c.evidence.find((e) => e.id === id);
    if (found) return found;
  }
  return undefined;
}

export function mockVerificationFor(e: EvidenceItem): Verification {
  const result: VerifyResult = e.verification ?? "pending";
  const anchored = result !== "pending";
  return {
    evidenceId: e.id,
    result,
    message: result === "verified" ? "Unchanged since anchoring on 2026-10-21 09:16 UTC" : "",
    expectedHash: e.sha256,
    recomputedHash: result === "altered" ? "ff".repeat(32) : e.sha256,
    onchainRoot: anchored ? "0x" + "ab".repeat(32) : null,
    computedRoot: anchored ? (result === "altered" ? "0x" + "12".repeat(32) : "0x" + "ab".repeat(32)) : null,
    txHash: anchored ? "0x" + "cd".repeat(32) : null,
    batchId: anchored ? "batch-1" : null,
    checkedAt: new Date().toISOString(),
  };
}

export function mockProofFor(e: EvidenceItem): Proof | null {
  if (e.status !== "anchored") return null;
  const tx = "0x" + "cd".repeat(32);
  return {
    evidenceId: e.id, batchId: "batch-1", leafIndex: 0, root: "0x" + "ab".repeat(32),
    txHash: tx, chainId: 80002, explorerUrl: `https://amoy.polygonscan.com/tx/${tx}`,
  };
}

const SAMPLE_CHAT = `[18/10/2026, 21:02] Unknown: Send 50,000 tonight or I will post your photos.
[18/10/2026, 21:03] Reporter: Who is this? Please stop.
[18/10/2026, 21:05] Unknown: You have until midnight.`;

export function mockBlobFor(e: EvidenceItem): Blob | null {
  if (e.mimeType.startsWith("text/")) return new Blob([SAMPLE_CHAT], { type: "text/plain" });
  if (e.mimeType.startsWith("image/")) {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="100%" height="100%" fill="#F1EEE7"/><text x="50%" y="50%" text-anchor="middle" font-family="sans-serif" font-size="20" fill="#5B6479">Sample screenshot: ${e.filename}</text></svg>`;
    return new Blob([svg], { type: "image/svg+xml" });
  }
  return null;
}