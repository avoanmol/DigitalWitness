import type {
  Analysis, CaseLink, Entity, EntityType, Flag, LinkStatus, ReviewStatus,
  Severity, SharedEntity, ThreatClass,
} from "@/lib/types";

// Decisions made during this browser session (mock mode only)
const flagStatus = new Map<string, ReviewStatus>();
const linkStatus = new Map<string, LinkStatus>();
export const setMockFlagStatus = (id: string, s: ReviewStatus) => { flagStatus.set(id, s); };
export const setMockLinkStatus = (id: string, s: LinkStatus) => { linkStatus.set(id, s); };

const ent = (
  id: string, type: EntityType, raw: string, normalised: string, confidence: number
): Entity => ({ id, type, raw, normalised, confidence });

const flag = (
  id: string, threatClass: ThreatClass, severity: Severity, snippet: string,
  confidence: number, reason: string
): Flag => ({ id, threatClass, severity, snippet, confidence, reason, reviewStatus: "pending" });

// Keys are evidence ids from fixtures.ts. Every snippet is an exact piece of its text.
const analyses: Record<string, Omit<Analysis, "evidenceId">> = {
  e1: {
    status: "done", language: "en",
    text: "Send 50,000 tonight or I will post your photos. You have until midnight. Message me on @dark_user77 or call +91 98765 43210.",
    entities: [
      ent("n1", "phone", "+91 98765 43210", "+919876543210", 0.95),
      ent("n2", "handle", "@dark_user77", "@dark_user77", 0.7),
    ],
    flags: [
      flag("f1", "extortion_blackmail", "high", "I will post your photos", 0.86,
        "Demands money and threatens to share private photos."),
      flag("f2", "harassment_stalking", "low", "You have until midnight", 0.35,
        "A pressure deadline. It may be part of the same threat."),
    ],
  },
  e2: {
    status: "done", language: "en",
    text: "Send 50,000 tonight or I will post your photos. Who is this? Please stop. You have until midnight.",
    entities: [ent("n3", "phone", "+91 98765 43210", "+919876543210", 0.9)],
    flags: [
      flag("f3", "extortion_blackmail", "high", "Send 50,000 tonight", 0.82,
        "A direct demand for money with a threat attached."),
    ],
  },
  e3: {
    status: "done", language: "en",
    text: "Your bank account will be blocked. Share the OTP now. Call +91 91234 56789 immediately.",
    entities: [ent("n4", "phone", "+91 91234 56789", "+919123456789", 0.9)],
    flags: [
      flag("f4", "fraud_scam", "medium", "Share the OTP now", 0.71,
        "Asks for a one-time password, a common scam pattern."),
    ],
  },
  e4: {
    status: "done", language: "en",
    text: "I know where you live. I will keep messaging you until you answer. Call +91 98765 43210 or find me at @dark_user77.",
    entities: [
      ent("n5", "phone", "+91 98765 43210", "+919876543210", 0.95),
      ent("n6", "handle", "@dark_user77", "@dark_user77", 0.7),
    ],
    flags: [
      flag("f5", "violence_threat", "critical", "I know where you live", 0.78,
        "Suggests the sender knows the reporter's home address."),
      flag("f6", "harassment_stalking", "medium", "I will keep messaging you", 0.64,
        "States an intent to keep contacting the reporter."),
    ],
  },
  e8: {
    status: "done", language: "en",
    text: "Voice note transcript: you will be followed home tonight.",
    entities: [],
    flags: [
      flag("f7", "violence_threat", "high", "you will be followed home", 0.74,
        "Describes being followed, which reads as a threat."),
    ],
  },
};

export function mockAnalysisFor(evidenceId: string): Analysis {
  const base = analyses[evidenceId] ?? {
    status: "done", language: "en", text: "", entities: [], flags: [],
  };
  return {
    evidenceId,
    ...base,
    flags: base.flags.map((f) => ({ ...f, reviewStatus: flagStatus.get(f.id) ?? f.reviewStatus })),
  };
}

// ---------- links between cases ----------
type RawLink = {
  id: string; a: string; b: string; shared: SharedEntity[];
  confidence: number; status: LinkStatus; createdBy: string;
};

const refOf = (caseId: string) => `DW-2026-${caseId.slice(1).padStart(4, "0")}`;

const rawLinks: RawLink[] = [
  {
    id: "l1", a: "c1", b: "c3", confidence: 0.95, status: "suggested", createdBy: "ai",
    shared: [
      { type: "phone", value: "+919876543210" },
      { type: "handle", value: "@dark_user77" },
    ],
  },
  {
    id: "l2", a: "c1", b: "c5", confidence: 0.7, status: "suggested", createdBy: "ai",
    shared: [{ type: "handle", value: "@dark_user77" }],
  },
  {
    id: "l3", a: "c3", b: "c5", confidence: 0.7, status: "suggested", createdBy: "ai",
    shared: [{ type: "handle", value: "@dark_user77" }],
  },
  {
    id: "l4", a: "c2", b: "c8", confidence: 0.6, status: "confirmed", createdBy: "u2",
    shared: [{ type: "url", value: "http://claim-prize.example/pay" }],
  },
];

export function mockLinksFor(caseId: string): CaseLink[] {
  return rawLinks
    .filter((l) => l.a === caseId || l.b === caseId)
    .map((l) => {
      const other = l.a === caseId ? l.b : l.a;
      return {
        id: l.id,
        otherCaseId: other,
        otherCaseRef: refOf(other),
        sharedEntities: l.shared,
        confidence: l.confidence,
        status: linkStatus.get(l.id) ?? l.status,
        createdBy: l.createdBy,
      };
    });
}