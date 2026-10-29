import type { AuditEntry, CaseDetail, CaseLink, ThreatFlag, User } from "@/lib/types";

const now = new Date().toISOString();
export const demoUsers: User[] = [
  { id: "demo-reporter", email: "demo.reporter@example.com", full_name: "Synthetic Reporter", role: "reporter", is_active: true },
  { id: "demo-investigator", email: "demo.investigator@example.com", full_name: "Synthetic Investigator", role: "investigator", is_active: true },
  { id: "demo-legal", email: "demo.legal@example.com", full_name: "Synthetic Legal Reviewer", role: "legal", is_active: true },
  { id: "demo-admin", email: "demo.admin@example.com", full_name: "Synthetic Administrator", role: "admin", is_active: true },
];

export const demoCases: CaseDetail[] = [
  {
    id: "case-demo-001", case_ref: "DW-2026-0001", title: "Repeated account impersonation",
    description: "Synthetic training report about a copied profile and threatening messages.", status: "under_review", created_at: now,
    evidence_count: 2, pending_count: 1, threat_count: 1, verification: "verified", threat_class: "impersonation", severity: "medium",
    evidence: [
      { id: "evidence-demo-001", case_id: "case-demo-001", filename: "sample-message.png", mime_type: "image/png", size_bytes: 248012, sha256: "81dc9bdb52d04dc20036dbd8313ed05581dc9bdb52d04dc20036dbd8313ed055", status: "anchored", uploaded_at: now, analysis_status: "done", verification: "verified", verification_message: "Unchanged since anchoring.", tx_hash: "0x4d28f138d062f0ccae94c555d26d50b84d5208711bcae90b1d6cb54eb38f028a", batch_id: "batch-demo-19", batch_root: "0x9907f49b36ca935163f0d72b23e20c123a5cda4e2285ebdc1d27f3fd1d26fc02", explorer_url: "https://amoy.polygonscan.com/tx/0x4d28f138d062f0ccae94c555d26d50b84d5208711bcae90b1d6cb54eb38f028a" },
      { id: "evidence-demo-002", case_id: "case-demo-001", filename: "follow-up.pdf", mime_type: "application/pdf", size_bytes: 88341, sha256: "c4ca4238a0b923820dcc509a6f75849bc4ca4238a0b923820dcc509a6f75849b", status: "stored", uploaded_at: now, analysis_status: "pending", verification: "pending", verification_message: "Waiting for an anchor." },
    ],
  },
  {
    id: "case-demo-002", case_ref: "DW-2026-0002", title: "Messages from an unknown sender",
    description: "Synthetic training report with a shared contact handle.", status: "open", created_at: now,
    evidence_count: 1, pending_count: 1, threat_count: 1, verification: "pending", threat_class: "extortion_blackmail", severity: "high",
    evidence: [{ id: "evidence-demo-003", case_id: "case-demo-002", filename: "chat-export.txt", mime_type: "text/plain", size_bytes: 19320, sha256: "eccbc87e4b5ce2fe28308fd9f2a7baf3eccbc87e4b5ce2fe28308fd9f2a7baf3", status: "stored", uploaded_at: now, analysis_status: "running", verification: "pending", verification_message: "Not anchored yet." }],
  },
  {
    id: "case-demo-003", case_ref: "DW-2026-0003", title: "Suspicious payment request",
    description: "Synthetic training report for an investigator workflow preview.", status: "closed", created_at: now,
    evidence_count: 1, pending_count: 0, threat_count: 0, verification: "altered", threat_class: "", severity: "",
    evidence: [{ id: "evidence-demo-004", case_id: "case-demo-003", filename: "payment-note.jpg", mime_type: "image/jpeg", size_bytes: 562010, sha256: "a87ff679a2f3e71d9181a67b7542122ca87ff679a2f3e71d9181a67b7542122c", status: "anchored", uploaded_at: now, analysis_status: "done", verification: "altered", verification_message: "The current file hash differs from the recorded hash." }],
  },
];

export const demoLinks: CaseLink[] = [{
  id: "link-demo-01", case_a_id: "case-demo-001", case_b_id: "case-demo-002", other_case_ref: "DW-2026-0002",
  other_case_title: "Messages from an unknown sender", confidence: 0.91, status: "suggested",
  shared_entities: [{ id: "entity-demo-01", type: "phone", raw: "+91 90000 10001", normalised: "+919000010001", confidence: 0.96 }],
}];

export const demoFlags: ThreatFlag[] = [
  { id: "flag-demo-01", evidence_id: "evidence-demo-001", threat_class: "impersonation", severity: "medium", snippet: "This profile is using the same display name and image.", confidence: 0.78, review_status: "pending" },
  { id: "flag-demo-02", evidence_id: "evidence-demo-003", threat_class: "extortion_blackmail", severity: "high", snippet: "Send the amount today or I will share the file.", confidence: 0.86, review_status: "pending" },
];

export const demoAudit: AuditEntry[] = [
  { id: "audit-demo-3", seq: 3, actor_role: "investigator", action: "verify_run", target_type: "evidence", target_id: "evidence-demo-001", case_id: "case-demo-001", details: { result: "verified" }, entry_hash: "75d01c9dcfb92a261a85c9535c87f2cb75d01c9dcfb92a261a85c9535c87f2cb", created_at: now },
  { id: "audit-demo-2", seq: 2, actor_role: "reporter", action: "evidence_upload", target_type: "evidence", target_id: "evidence-demo-001", case_id: "case-demo-001", details: { filename: "sample-message.png" }, entry_hash: "b172f900ec3e4b62d8dc5f89d3401b19b172f900ec3e4b62d8dc5f89d3401b19", created_at: now },
  { id: "audit-demo-1", seq: 1, actor_role: "reporter", action: "case_create", target_type: "case", target_id: "case-demo-001", case_id: "case-demo-001", details: {}, entry_hash: "85f64f06a0f0bb65d038bc44169e1a0185f64f06a0f0bb65d038bc44169e1a01", created_at: now },
];
