export type Role = "reporter" | "investigator" | "legal" | "admin";
export type CaseStatus = "open" | "under_review" | "closed";
export type EvidenceStatus = "received" | "stored" | "anchored" | "failed";
export type VerificationResult = "verified" | "altered" | "pending" | "not_checked" | "error";
export type ReviewStatus = "pending" | "confirmed" | "rejected";
export type FlagReviewReason =
  | "source_supports_flag"
  | "reported_or_quoted_context"
  | "educational_or_hypothetical_context"
  | "wrong_category"
  | "snippet_not_supported"
  | "extraction_unclear"
  | "duplicate_or_repeated"
  | "insufficient_context"
  | "other";
export type LinkReviewReason =
  | "source_supports_connection"
  | "shared_identifier_is_common"
  | "different_account_or_person"
  | "separate_context"
  | "insufficient_context"
  | "other";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export interface CaseSummary {
  id: string;
  case_ref: string;
  title: string;
  description: string | null;
  status: CaseStatus;
  created_at: string;
  evidence_count: number;
  pending_count: number;
  threat_count: number;
  verification: VerificationResult | null;
  threat_class?: string | null;
  severity?: string | null;
}

export interface EvidenceSummary {
  id: string;
  case_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  status: EvidenceStatus;
  uploaded_at: string;
  analysis_status: "pending" | "running" | "done" | "failed" | "skipped";
  verification: VerificationResult;
  verification_message?: string;
  tx_hash?: string | null;
  batch_id?: string | null;
  chain_batch_id?: string | null;
  chain_id?: number | null;
  batch_root?: string | null;
  explorer_url?: string | null;
}

export interface CaseDetail extends CaseSummary {
  evidence: EvidenceSummary[];
}

export interface CaseInvestigationSummary {
  case_id: string;
  case_ref: string;
  generated_at: string;
  overview: string;
  evidence_count: number;
  analysed_count: number;
  needs_analysis_count: number;
  pending_flag_count: number;
  categories: {
    category: string;
    evidence_ids: string[];
    focus_evidence_ids: string[];
    flag_evidence_ids: string[];
    flag_count: number;
    pending_count: number;
    confirmed_count: number;
    rejected_count: number;
  }[];
  evidence: {
    evidence_id: string;
    filename: string;
    uploaded_at: string;
    analysis_status: string;
    language: string | null;
    extraction_method: string | null;
    coverage: ExtractionCoverage | null;
    focus_categories: string[];
    flags: {
      id: string;
      category: string;
      severity: string;
      snippet: string;
      review_status: ReviewStatus;
      review_reason?: string | null;
    }[];
  }[];
  limitations: string[];
}

export type ComplaintChannel = "cybercrime_portal" | "local_police";

export interface ExternalComplaintReference {
  saved: boolean;
  channel: ComplaintChannel | null;
  last_four: string | null;
  updated_at: string | null;
  reference?: string | null;
}

export interface ComplaintEvidenceItem {
  evidence_id: string;
  filename: string;
  sha256: string;
  uploaded_at: string;
  file_status: string;
  analysis_status: string;
  verification: string;
  anchor_status: string;
  chain_id: number | null;
  transaction_hash: string | null;
}

export interface ComplaintAiNote {
  flag_id: string;
  evidence_id: string;
  filename: string;
  category: string;
  severity: string;
  review_status: ReviewStatus;
  snippet: string;
}

export interface ComplaintAiNoteFeedback {
  flag_id: string;
  include: boolean;
  reporter_comment?: string;
}

export interface ComplaintPreview {
  case_id: string;
  case_ref: string;
  case_title: string;
  incident_date_on_record: string | null;
  generated_at: string;
  evidence: ComplaintEvidenceItem[];
  ai_notes: ComplaintAiNote[];
  analysis_pending_count: number;
  analysis_unavailable_count: number;
  limitations: string[];
}

export interface ComplaintPacketInput {
  channel: ComplaintChannel;
  incident_date?: string;
  incident_time?: string;
  timezone_note?: string;
  platform: string;
  account_or_handle?: string;
  profile_url?: string;
  state?: string;
  district?: string;
  police_station?: string;
  statement: string;
  ai_note_feedback?: ComplaintAiNoteFeedback[];
  reviewed_evidence_and_notes: boolean;
  understands_not_submitted: boolean;
}

export interface Receipt {
  receipt_id: string;
  case_ref: string;
  case_id: string;
  evidence_id: string;
  filename: string;
  size_bytes: number;
  sha256: string;
  uploaded_at: string;
  status: EvidenceStatus;
  signature: string;
  signature_valid?: boolean;
  investigation_categories?: string[];
}

export interface Verification {
  evidence_id: string;
  verification_id?: string;
  chain_batch_id?: string | null;
  result: VerificationResult;
  message: string;
  expected_hash: string | null;
  recomputed_hash: string | null;
  onchain_root: string | null;
  computed_root: string | null;
  tx_hash: string | null;
  batch_id: string | null;
  checked_at: string;
}

export interface Entity {
  id: string;
  type: string;
  raw: string;
  normalised: string;
  confidence: number;
}

export interface ThreatFlag {
  id: string;
  evidence_id: string;
  threat_class: string;
  severity: "low" | "medium" | "high" | "critical";
  snippet: string;
  reason?: string | null;
  confidence: number;
  review_status: ReviewStatus;
  review_reason?: FlagReviewReason | null;
}

export interface ReviewInsightBucket {
  label: string;
  confirmed: number;
  rejected: number;
  total: number;
}

export interface ReviewInsights {
  source: "human_review_feedback";
  reviewed_flag_count: number;
  outcomes: { confirmed: number; rejected: number };
  by_category: ReviewInsightBucket[];
  by_language: ReviewInsightBucket[];
  by_media_type: ReviewInsightBucket[];
  by_review_reason: ReviewInsightBucket[];
  training_enabled: false;
  limitations: string[];
}

export interface ExtractionCoverage {
  status: "text_extracted" | "partial" | "sampled" | "no_text" | "extraction_failed";
  method?: string | null;
  characters_extracted: number;
  truncated: boolean;
  units_examined?: number | null;
  units_total?: number | null;
  duration_seconds?: number | null;
  notes: string[];
}

export interface CaseLink {
  id: string;
  case_a_id: string;
  case_b_id: string;
  other_case_ref: string;
  other_case_title: string;
  shared_entities: Entity[];
  confidence: number;
  status: "suggested" | "confirmed" | "rejected";
  review_reason?: LinkReviewReason | null;
}

export interface Analysis {
  evidence_id: string;
  status: string;
  language: string | null;
  text: string | null;
  model?: string | null;
  prompt_version?: string | null;
  analysis_source?: string | null;
  human_review_required?: boolean;
  extraction_method?: string | null;
  investigation_categories?: string[];
  coverage?: ExtractionCoverage | null;
  provenance?: {
    file_format?: string;
    metadata_present?: boolean;
    dimensions?: { width: number; height: number };
    page_count?: number;
    observations?: string[];
    caveat?: string;
  } | null;
  video?: {
    duration_seconds?: number;
    frames_examined?: number;
    frames_examined_limit?: number;
    sampled_timestamps_seconds?: number[];
    video_codec?: string;
    frame_width?: number | null;
    frame_height?: number | null;
    frame_rate?: number | null;
    caveat?: string;
  } | null;
  entities: Entity[];
  flags: ThreatFlag[];
}

export interface AuditEntry {
  id: string;
  seq: number;
  actor_role: string | null;
  action: string;
  target_type: string;
  target_id: string | null;
  case_id: string | null;
  details: Record<string, unknown>;
  entry_hash: string;
  created_at: string;
}

export interface CaseActivityEvent {
  id: string;
  kind: string;
  title: string;
  description: string;
  created_at: string;
  actor_role: string | null;
  evidence_id: string | null;
}

export interface PageResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface CaseFilters {
  q?: string;
  status?: CaseStatus | "";
  from?: string;
  to?: string;
  threat_class?: string;
  severity?: string;
  verification?: VerificationResult | "";
  page?: number;
  page_size?: number;
}
