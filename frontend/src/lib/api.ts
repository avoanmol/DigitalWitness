import { demoAudit, demoCases, demoFlags, demoLinks, demoUsers } from "@/mocks/fixtures";
import { getAccessToken, setSession } from "@/lib/session";
import type { Analysis, AuditEntry, CaseActivityEvent, CaseDetail, CaseFilters, CaseInvestigationSummary, CaseLink, CaseSummary, ComplaintPacketInput, ComplaintPreview, EvidenceSummary, ExternalComplaintReference, FlagReviewReason, LinkReviewReason, PageResult, Receipt, ReviewInsights, Role, User, Verification } from "@/lib/types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";
const MAX_UPLOAD_MB = Number(process.env.NEXT_PUBLIC_MAX_UPLOAD_MB || 100);

export class ApiError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

export function isMockMode() { return MOCK; }
export function uploadLimitMb() { return MAX_UPLOAD_MB; }

function messageFromError(body: unknown, fallback: string): string {
  if (body && typeof body === "object") {
    const record = body as { detail?: unknown; error?: { message?: unknown } };
    if (typeof record.error?.message === "string") return record.error.message;
    if (typeof record.detail === "string") return record.detail;
    if (Array.isArray(record.detail) && record.detail.length > 0) {
      const issue = record.detail[0] as { msg?: unknown };
      if (typeof issue?.msg === "string") return issue.msg;
    }
  }
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getAccessToken();
  if (token && !headers.has("Authorization")) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  headers.set("Accept", headers.get("Accept") || "application/json");
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers, cache: "no-store" });
  } catch {
    throw new ApiError("The API could not be reached. Check that FastAPI is running and the API URL is correct.");
  }
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      message = messageFromError(await response.json(), message);
    } catch { /* Keep the status message when the server did not return JSON. */ }
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}

function normalizeUser(data: Partial<User> & { id?: string; email?: string; role?: string; full_name?: string }): User {
  const role = ["reporter", "investigator", "legal", "admin"].includes(data.role || "") ? data.role as Role : "reporter";
  return { id: data.id || "unknown", email: data.email || "", full_name: data.full_name || "DigitalWitness user", role, is_active: data.is_active !== false };
}

function normalizeEvidence(item: Record<string, unknown>, caseId: string): EvidenceSummary {
  const status = String(item.status || "stored") as EvidenceSummary["status"];
  return {
    id: String(item.id || item.evidence_id || ""), case_id: String(item.case_id || caseId),
    filename: String(item.filename || item.original_filename || "Evidence file"),
    mime_type: String(item.mime_type || "application/octet-stream"), size_bytes: Number(item.size_bytes || 0),
    sha256: String(item.sha256 || ""), status, uploaded_at: String(item.uploaded_at || new Date().toISOString()),
    analysis_status: (item.analysis_status || "pending") as EvidenceSummary["analysis_status"],
    verification: (item.verification || (status === "anchored" ? "not_checked" : "pending")) as EvidenceSummary["verification"],
    verification_message: typeof item.verification_message === "string" ? item.verification_message : undefined,
    tx_hash: typeof item.tx_hash === "string" ? item.tx_hash : null,
    batch_id: typeof item.batch_id === "string" ? item.batch_id : null,
    chain_batch_id: typeof item.chain_batch_id === "string" ? item.chain_batch_id : null,
    chain_id: typeof item.chain_id === "number" ? item.chain_id : null,
    batch_root: typeof item.batch_root === "string" ? item.batch_root : null,
    explorer_url: typeof item.explorer_url === "string" ? item.explorer_url : null,
  };
}

function normalizeCase(item: Record<string, unknown>): CaseSummary {
  return {
    id: String(item.id || ""), case_ref: String(item.case_ref || "Case"), title: String(item.title || "Untitled case"),
    description: typeof item.description === "string" ? item.description : null,
    status: (item.status || "open") as CaseSummary["status"], created_at: String(item.created_at || new Date().toISOString()),
    evidence_count: Number(item.evidence_count || (Array.isArray(item.evidence) ? item.evidence.length : 0)),
    pending_count: Number(item.pending_count || 0), threat_count: Number(item.threat_count || 0),
    verification: (item.verification || null) as CaseSummary["verification"],
    threat_class: typeof item.threat_class === "string" ? item.threat_class : null,
    severity: typeof item.severity === "string" ? item.severity : null,
  };
}

export async function signIn(email: string, password: string): Promise<User> {
  if (MOCK) {
    const user = demoUsers.find((candidate) => candidate.email.toLowerCase() === email.toLowerCase()) || demoUsers[0];
    setSession("mock-session", user);
    return user;
  }
  const data = await request<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
  const user = normalizeUser(await request<User>("/auth/me", { headers: { Authorization: `Bearer ${data.access_token}` } }));
  setSession(data.access_token, user);
  return user;
}

export async function registerReporter(fullName: string, email: string, password: string): Promise<User> {
  if (MOCK) {
    const user = { id: `mock-${Date.now()}`, email, full_name: fullName, role: "reporter" as const, is_active: true };
    demoUsers.push(user);
    setSession("mock-session", user);
    return user;
  }
  await request<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, full_name: fullName, password }) });
  return signIn(email, password);
}

export async function getCases(filters: CaseFilters = {}): Promise<PageResult<CaseSummary>> {
  if (MOCK) {
    const q = (filters.q || "").toLowerCase();
    const filtered = demoCases.filter((item) => {
      if (q && !`${item.case_ref} ${item.title} ${item.id}`.toLowerCase().includes(q)) return false;
      if (filters.status && item.status !== filters.status) return false;
      if (filters.verification && item.verification !== filters.verification) return false;
      if (filters.threat_class && item.threat_class !== filters.threat_class) return false;
      if (filters.severity && item.severity !== filters.severity) return false;
      if (filters.from && new Date(item.created_at) < new Date(filters.from)) return false;
      if (filters.to && new Date(item.created_at) > new Date(`${filters.to}T23:59:59`)) return false;
      return true;
    });
    const page = filters.page || 1;
    const pageSize = filters.page_size || 8;
    return { items: filtered.slice((page - 1) * pageSize, page * pageSize), total: filtered.length, page, page_size: pageSize };
  }
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => { if (value !== undefined && value !== "") params.set(key, String(value)); });
  const data = await request<CaseSummary[] | { items: CaseSummary[]; total: number; page: number; page_size: number }>(`/cases?${params}`);
  if (Array.isArray(data)) return { items: data.map((item) => normalizeCase(item as unknown as Record<string, unknown>)), total: data.length, page: 1, page_size: data.length };
  return { ...data, items: data.items.map((item) => normalizeCase(item as unknown as Record<string, unknown>)) };
}

export async function createCase(payload: { title: string; description: string }): Promise<CaseSummary> {
  if (MOCK) {
    const item: CaseDetail = {
      id: `case-${crypto.randomUUID()}`, case_ref: `DW-2026-${String(demoCases.length + 1).padStart(4, "0")}`,
      title: payload.title, description: payload.description || null, status: "open", created_at: new Date().toISOString(),
      evidence_count: 0, pending_count: 0, threat_count: 0, verification: null, evidence: [],
    };
    demoCases.unshift(item);
    return item;
  }
  const data = await request<Record<string, unknown>>("/cases", { method: "POST", body: JSON.stringify(payload) });
  return normalizeCase(data);
}

function saveReceipt(receipt: Receipt) {
  if (typeof window !== "undefined") window.sessionStorage.setItem(`dw-receipt:${receipt.receipt_id}`, JSON.stringify(receipt));
}

export async function uploadEvidence(caseItem: CaseSummary, file: File, onProgress: (percent: number) => void, signal?: AbortSignal, investigationCategories: string[] = []): Promise<Receipt> {
  if (MOCK) {
    const hash = [...new Uint8Array(await crypto.subtle.digest("SHA-256", await file.arrayBuffer()))].map((value) => value.toString(16).padStart(2, "0")).join("");
    if (signal?.aborted) throw new DOMException("Upload cancelled", "AbortError");
    for (const progress of [20, 48, 76, 100]) {
      await new Promise((resolve) => setTimeout(resolve, 90));
      if (signal?.aborted) throw new DOMException("Upload cancelled", "AbortError");
      onProgress(progress);
    }
    const evidenceId = `evidence-${crypto.randomUUID()}`;
    const evidence = normalizeEvidence({ id: evidenceId, case_id: caseItem.id, filename: file.name, mime_type: file.type, size_bytes: file.size, sha256: hash, status: "stored", uploaded_at: new Date().toISOString(), analysis_status: "pending", verification: "pending" }, caseItem.id);
    const target = demoCases.find((item) => item.id === caseItem.id);
    if (target) { target.evidence.unshift(evidence); target.evidence_count += 1; target.pending_count += 1; }
    mockFiles.set(evidenceId, file);
    const receipt: Receipt = { receipt_id: evidenceId, case_ref: caseItem.case_ref, case_id: caseItem.id, evidence_id: evidenceId, filename: file.name, size_bytes: file.size, sha256: hash, uploaded_at: evidence.uploaded_at, status: "stored", signature: "MOCK MODE - not a server receipt", investigation_categories: investigationCategories };
    saveReceipt(receipt);
    return receipt;
  }
  const form = new FormData();
  form.append("file", file);
  const token = getAccessToken();
  const params = new URLSearchParams({ case_id: caseItem.id });
  for (const category of investigationCategories) params.append("investigation_categories", category);
  const url = `${API_URL}/evidence/upload?${params.toString()}`;
  const data = await new Promise<Record<string, unknown>>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.setRequestHeader("Accept", "application/json");
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (event) => { if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100)); };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) { try { resolve(JSON.parse(xhr.responseText)); } catch { reject(new ApiError("The API returned an invalid upload response.")); } }
      else {
        let message = `Upload failed (${xhr.status}).`;
        try { message = messageFromError(JSON.parse(xhr.responseText), message); } catch { /* Keep status. */ }
        reject(new ApiError(message, xhr.status));
      }
    };
    xhr.onerror = () => reject(new ApiError("Upload failed because the API could not be reached."));
    xhr.onabort = () => reject(new DOMException("Upload cancelled", "AbortError"));
    signal?.addEventListener("abort", () => xhr.abort(), { once: true });
    xhr.send(form);
  });
  const receipt: Receipt = {
    receipt_id: String(data.id), case_ref: caseItem.case_ref, case_id: caseItem.id, evidence_id: String(data.id),
    filename: String(data.filename || file.name), size_bytes: Number(data.size_bytes || file.size), sha256: String(data.sha256 || ""),
    uploaded_at: String(data.uploaded_at || new Date().toISOString()), status: String(data.status || "stored") as Receipt["status"],
    signature: String(data.receipt_signature || data.signature || ""),
    signature_valid: data.signature_valid === true,
    investigation_categories: Array.isArray(data.investigation_categories) ? data.investigation_categories.map(String) : investigationCategories,
  };
  saveReceipt(receipt);
  return receipt;
}

export async function getReceipt(id: string): Promise<Receipt> {
  if (typeof window !== "undefined") {
    const saved = window.sessionStorage.getItem(`dw-receipt:${id}`);
    if (saved) return JSON.parse(saved) as Receipt;
  }
  if (MOCK) throw new ApiError("Receipt not found in this demo session.", 404);
  return request<Receipt>(`/evidence/${encodeURIComponent(id)}/receipt`);
}

export async function getCase(id: string): Promise<CaseDetail> {
  if (MOCK) {
    const item = demoCases.find((candidate) => candidate.id === id);
    if (!item) throw new ApiError("Case not found.", 404);
    return structuredClone(item);
  }
  const data = await request<Record<string, unknown>>(`/cases/${encodeURIComponent(id)}`);
  const base = normalizeCase(data);
  const evidence = Array.isArray(data.evidence) ? data.evidence.map((row) => normalizeEvidence(row as Record<string, unknown>, id)) : [];
  return { ...base, evidence };
}

export async function getCaseActivity(caseId: string): Promise<CaseActivityEvent[]> {
  if (MOCK) {
    const item = demoCases.find((candidate) => candidate.id === caseId);
    if (!item) throw new ApiError("Case not found.", 404);
    const events: CaseActivityEvent[] = [{
      id: `case-created:${item.id}`, kind: "case_created", title: "Case created",
      description: "The case was opened in DigitalWitness.", created_at: item.created_at,
      actor_role: "reporter", evidence_id: null,
    }];
    for (const evidence of item.evidence) {
      events.push({
        id: `evidence-uploaded:${evidence.id}`, kind: "evidence_uploaded", title: "Evidence uploaded",
        description: evidence.filename, created_at: evidence.uploaded_at,
        actor_role: "reporter", evidence_id: evidence.id,
      });
    }
    for (const entry of demoAudit.filter((candidate) => candidate.case_id === caseId && candidate.action === "verify_run")) {
      const evidence = item.evidence.find((candidate) => candidate.id === entry.target_id);
      events.push({
        id: entry.id, kind: "evidence.verify", title: "Integrity check completed",
        description: `${evidence?.filename ? `${evidence.filename}: ` : ""}Integrity check result: ${String(entry.details.result || "recorded")}.`,
        created_at: entry.created_at, actor_role: entry.actor_role, evidence_id: entry.target_id,
      });
    }
    return events.sort((left, right) => right.created_at.localeCompare(left.created_at));
  }
  return request<CaseActivityEvent[]>(`/cases/${encodeURIComponent(caseId)}/activity`);
}

export async function getCaseInvestigationSummary(caseId: string): Promise<CaseInvestigationSummary> {
  if (MOCK) {
    const caseItem = await getCase(caseId);
    const analyses = await Promise.all(caseItem.evidence.map((evidence) => getAnalysis(evidence.id)));
    const evidence = caseItem.evidence.map((item, index) => ({
      evidence_id: item.id,
      filename: item.filename,
      uploaded_at: item.uploaded_at,
      analysis_status: analyses[index].status,
      language: analyses[index].language,
      extraction_method: analyses[index].extraction_method || null,
      coverage: analyses[index].coverage || null,
      focus_categories: analyses[index].investigation_categories || [],
      flags: analyses[index].flags.map((flag) => ({
        id: flag.id, category: flag.threat_class, severity: flag.severity,
        snippet: flag.snippet, review_status: flag.review_status,
        review_reason: flag.review_reason || null,
      })),
    }));
    const categories = new Map<string, CaseInvestigationSummary["categories"][number]>();
    for (const item of evidence) for (const category of new Set([...item.focus_categories, ...item.flags.map((flag) => flag.category)])) {
      const row = categories.get(category) || { category, evidence_ids: [], focus_evidence_ids: [], flag_evidence_ids: [], flag_count: 0, pending_count: 0, confirmed_count: 0, rejected_count: 0 };
      if (!row.evidence_ids.includes(item.evidence_id)) row.evidence_ids.push(item.evidence_id);
      if (item.focus_categories.includes(category) && !row.focus_evidence_ids.includes(item.evidence_id)) row.focus_evidence_ids.push(item.evidence_id);
      if (item.flags.some((flag) => flag.category === category) && !row.flag_evidence_ids.includes(item.evidence_id)) row.flag_evidence_ids.push(item.evidence_id);
      for (const flag of item.flags.filter((candidate) => candidate.category === category)) {
        row.flag_count += 1;
        row[`${flag.review_status}_count` as "pending_count" | "confirmed_count" | "rejected_count"] += 1;
      }
      categories.set(category, row);
    }
    const analysed = evidence.filter((item) => item.analysis_status === "done").length;
    const pendingFlags = evidence.flatMap((item) => item.flags).filter((flag) => flag.review_status === "pending").length;
    return {
      case_id: caseItem.id, case_ref: caseItem.case_ref, generated_at: new Date().toISOString(),
      overview: `${evidence.length} evidence item(s) are attached; ${analysed} have completed analysis, ${evidence.length - analysed} are pending, failed, or skipped, and ${pendingFlags} suggested flag(s) still need human review.`,
      evidence_count: evidence.length, analysed_count: analysed, needs_analysis_count: evidence.length - analysed,
      pending_flag_count: pendingFlags, categories: [...categories.values()].sort((a, b) => a.category.localeCompare(b.category)),
      evidence, limitations: ["This is a deterministic rollup of stored records, not a finding that an event occurred.", "Selected focus categories are reporter-provided context and do not prove a category applies.", "Review the original evidence and extraction coverage before interpreting any snippet."],
    };
  }
  return request<CaseInvestigationSummary>(`/cases/${encodeURIComponent(caseId)}/investigative-summary`);
}

export async function getComplaintPreview(caseId: string): Promise<ComplaintPreview> {
  if (MOCK) {
    const item = await getCase(caseId);
    const visibleEvidence = item.evidence.map((evidence) => ({
      evidence_id: evidence.id, filename: evidence.filename, sha256: evidence.sha256,
      uploaded_at: evidence.uploaded_at, file_status: evidence.status,
      analysis_status: evidence.analysis_status, verification: evidence.verification,
      anchor_status: evidence.status === "anchored" ? "confirmed" : "not anchored",
      chain_id: evidence.chain_id || null, transaction_hash: evidence.tx_hash || null,
    }));
    const ids = new Set(item.evidence.map((evidence) => evidence.id));
    const notes = demoFlags.filter((flag) => ids.has(flag.evidence_id) && flag.review_status !== "rejected").map((flag) => ({
      flag_id: flag.id,
      evidence_id: flag.evidence_id,
      filename: item.evidence.find((evidence) => evidence.id === flag.evidence_id)?.filename || "Case evidence",
      category: flag.threat_class, severity: flag.severity,
      review_status: flag.review_status, snippet: flag.snippet,
    }));
    return {
      case_id: item.id, case_ref: item.case_ref, case_title: item.title,
      incident_date_on_record: null, generated_at: new Date().toISOString(),
      evidence: visibleEvidence, ai_notes: notes,
      analysis_pending_count: visibleEvidence.filter((evidence) => ["pending", "running"].includes(evidence.analysis_status)).length,
      analysis_unavailable_count: visibleEvidence.filter((evidence) => ["failed", "skipped"].includes(evidence.analysis_status)).length,
      limitations: [
        "AI notes are automated leads and may be wrong; they do not establish that a crime occurred.",
        "Integrity status concerns the saved file fingerprint / anchor only. It does not prove the original file is authentic.",
        "Review the listed original files and excerpts. Original files are not embedded in the complaint packet.",
        "DigitalWitness does not send a complaint or select a legal outcome for you.",
      ],
    };
  }
  return request<ComplaintPreview>(`/cases/${encodeURIComponent(caseId)}/complaint-preview`);
}

export async function downloadComplaintPacket(caseId: string, caseRef: string, details: ComplaintPacketInput): Promise<{ digest: string | null; format: "pdf" | "utf-8-text" }> {
  let blob: Blob;
  let digest: string | null = null;
  let format: "pdf" | "utf-8-text" = "pdf";
  if (MOCK) {
    const preview = await getComplaintPreview(caseId);
    blob = makeMockPdf([
      "DigitalWitness complaint packet draft - SYNTHETIC DATA",
      `DRAFT FOR REPORTER REVIEW - NOT SUBMITTED. Case ${preview.case_ref}: ${preview.case_title}`,
      `Selected channel: ${details.channel === "cybercrime_portal" ? "Official Cyber Crime Portal" : "Local police"}`,
      `Platform: ${details.platform}`,
      `Incident date: ${details.incident_date || "Not provided"}`,
      `Statement: ${details.statement}`,
      ...preview.evidence.map((evidence) => `${evidence.filename} | SHA-256 ${evidence.sha256} | ${evidence.verification} / ${evidence.anchor_status}`),
      ...preview.ai_notes.flatMap((note) => {
        const feedback = details.ai_note_feedback?.find((item) => item.flag_id === note.flag_id);
        if (feedback && !feedback.include) return [];
        return [`AI suggestion (${note.review_status}): ${note.category} / ${note.severity} — ${note.snippet}${feedback?.reporter_comment ? `\nReporter correction / context: ${feedback.reporter_comment}` : ""}`];
      }),
      "AI notes are not proof or a legal conclusion. Verified means matching the saved fingerprint / anchor only.",
      "The original evidence files are not embedded. The reporter must review and submit this packet themself.",
    ]);
  } else {
    const token = getAccessToken();
    const headers = new Headers({ Accept: "application/pdf", "Content-Type": "application/json" });
    if (token) headers.set("Authorization", `Bearer ${token}`);
    let response: Response;
    try {
      response = await fetch(`${API_URL}/cases/${encodeURIComponent(caseId)}/complaint-packet`, {
        method: "POST", headers, body: JSON.stringify(details), cache: "no-store",
      });
    } catch {
      throw new ApiError("The API could not be reached. Check that FastAPI is running and the API URL is correct.");
    }
    if (!response.ok) {
      let message = `Could not prepare the complaint packet (${response.status}).`;
      try { message = messageFromError(await response.json(), message); } catch { /* Keep the status message. */ }
      throw new ApiError(message, response.status);
    }
    blob = await response.blob();
    digest = response.headers.get("X-Complaint-Packet-SHA256");
    format = response.headers.get("X-Complaint-Packet-Format") === "utf-8-text" || response.headers.get("content-type")?.startsWith("text/plain")
      ? "utf-8-text"
      : "pdf";
  }
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${caseRef}-complaint-draft.${format === "pdf" ? "pdf" : "txt"}`;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  return { digest, format };
}

const mockExternalReferences = new Map<string, ExternalComplaintReference>();
const mockExternalReferenceValues = new Map<string, string>();

export async function getExternalComplaintReference(caseId: string, reveal = false): Promise<ExternalComplaintReference> {
  if (MOCK) {
    const summary = mockExternalReferences.get(caseId) || { saved: false, channel: null, last_four: null, updated_at: null };
    return structuredClone(reveal ? { ...summary, reference: mockExternalReferenceValues.get(caseId) || null } : summary);
  }
  return request<ExternalComplaintReference>(`/cases/${encodeURIComponent(caseId)}/external-reference${reveal ? "?reveal=true" : ""}`);
}

export async function saveExternalComplaintReference(caseId: string, input: { channel: "cybercrime_portal" | "local_police"; reference: string }): Promise<ExternalComplaintReference> {
  if (MOCK) {
    const saved = { saved: true, channel: input.channel, last_four: input.reference.slice(-4), updated_at: new Date().toISOString() } satisfies ExternalComplaintReference;
    mockExternalReferences.set(caseId, saved);
    mockExternalReferenceValues.set(caseId, input.reference);
    return structuredClone(saved);
  }
  return request<ExternalComplaintReference>(`/cases/${encodeURIComponent(caseId)}/external-reference`, {
    method: "PUT", body: JSON.stringify(input),
  });
}

export async function deleteExternalComplaintReference(caseId: string): Promise<ExternalComplaintReference> {
  if (MOCK) {
    const removed = { saved: false, channel: null, last_four: null, updated_at: null } satisfies ExternalComplaintReference;
    mockExternalReferences.set(caseId, removed);
    mockExternalReferenceValues.delete(caseId);
    return structuredClone(removed);
  }
  return request<ExternalComplaintReference>(`/cases/${encodeURIComponent(caseId)}/external-reference`, { method: "DELETE" });
}

export async function getEvidence(id: string): Promise<EvidenceSummary> {
  if (MOCK) {
    const evidence = demoCases.flatMap((item) => item.evidence).find((item) => item.id === id);
    if (!evidence) throw new ApiError("Evidence not found.", 404);
    return structuredClone(evidence);
  }
  const data = await request<Record<string, unknown>>(`/evidence/${encodeURIComponent(id)}`);
  return normalizeEvidence(data, String(data.case_id || ""));
}

const mockFiles = new Map<string, File>();
export async function getEvidenceFile(id: string): Promise<Blob> {
  if (MOCK) return mockFiles.get(id) || new Blob(["Synthetic demo preview. This is sample content only."], { type: "text/plain" });
  const token = getAccessToken();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}/evidence/${encodeURIComponent(id)}/file`, { headers, cache: "no-store" });
  if (!response.ok) {
    let message = `Could not load evidence (${response.status}).`;
    try { message = messageFromError(await response.json(), message); } catch { /* Keep the status message. */ }
    throw new ApiError(message, response.status);
  }
  return response.blob();
}

export async function verifyEvidence(id: string): Promise<Verification> {
  if (MOCK) {
    const evidence = await getEvidence(id);
    const result = evidence.verification;
    return { evidence_id: id, result, message: result === "verified" ? "Unchanged since anchoring." : result === "altered" ? "The current file hash differs from the recorded hash." : result === "pending" ? "Not anchored yet." : "Verification could not be completed.", expected_hash: evidence.sha256, recomputed_hash: result === "verified" ? evidence.sha256 : null, onchain_root: evidence.batch_root || null, computed_root: evidence.batch_root || null, tx_hash: evidence.tx_hash || null, batch_id: evidence.batch_id || null, checked_at: new Date().toISOString() };
  }
  return request<Verification>(`/evidence/${encodeURIComponent(id)}/verify`, { method: "POST" });
}

export async function getLinks(caseId: string): Promise<CaseLink[]> {
  if (MOCK) return structuredClone(demoLinks.filter((link) => link.case_a_id === caseId || link.case_b_id === caseId));
  const data = await request<CaseLink[] | { items: CaseLink[] }>(`/cases/${encodeURIComponent(caseId)}/links`);
  const links = Array.isArray(data) ? data : data.items;
  return Promise.all(links.map(async (link) => {
    const otherId = link.case_a_id === caseId ? link.case_b_id : link.case_a_id;
    if (link.other_case_ref && link.other_case_title) return link;
    try {
      const related = normalizeCase(await request<Record<string, unknown>>(`/cases/${encodeURIComponent(otherId)}`));
      return { ...link, other_case_ref: related.case_ref, other_case_title: related.title };
    } catch {
      return { ...link, other_case_ref: link.other_case_ref || otherId.slice(0, 12), other_case_title: link.other_case_title || "Related case" };
    }
  }));
}

export async function updateLink(id: string, status: "confirmed" | "rejected", review_reason: LinkReviewReason): Promise<void> {
  if (MOCK) { const link = demoLinks.find((item) => item.id === id); if (link) { link.status = status; link.review_reason = review_reason; } return; }
  await request(`/links/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ status, review_reason }) });
}

export async function createLink(caseId: string, otherCaseId: string, note: string): Promise<void> {
  const [case_a_id, case_b_id] = [caseId, otherCaseId].sort((left, right) => left.localeCompare(right));
  if (MOCK) {
    const other = demoCases.find((item) => item.id === otherCaseId);
    if (!other) throw new ApiError("Select a case from the list.");
    demoLinks.push({ id: `link-${crypto.randomUUID()}`, case_a_id, case_b_id, other_case_ref: other.case_ref, other_case_title: other.title, shared_entities: [{ id: crypto.randomUUID(), type: "note", raw: note || "Manually linked by investigator", normalised: note || "Manually linked by investigator", confidence: 1 }], confidence: 1, status: "suggested" });
    return;
  }
  await request("/links", { method: "POST", body: JSON.stringify({ case_a_id, case_b_id, note }) });
}

export async function getAnalysis(evidenceId: string): Promise<Analysis> {
  if (MOCK) return { evidence_id: evidenceId, status: "done", language: "en", text: "Synthetic training content only.", entities: [], flags: demoFlags.filter((flag) => flag.evidence_id === evidenceId).map((flag) => ({ ...flag })) };
  return request<Analysis>(`/evidence/${encodeURIComponent(evidenceId)}/analysis`);
}

export async function requestAnalysis(evidenceId: string): Promise<Analysis> {
  if (MOCK) return getAnalysis(evidenceId);
  return request<Analysis>("/evidence/" + encodeURIComponent(evidenceId) + "/analyse", { method: "POST" });
}

export async function updateFlag(id: string, reviewStatus: "confirmed" | "rejected", reviewReason: FlagReviewReason = "other"): Promise<void> {
  if (MOCK) { const flag = demoFlags.find((item) => item.id === id); if (flag) { flag.review_status = reviewStatus; flag.review_reason = reviewReason; } return; }
  await request(`/flags/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ review_status: reviewStatus, review_reason: reviewReason }) });
}

export async function getReviewInsights(): Promise<ReviewInsights> {
  if (MOCK) {
    const evidenceById = new Map(demoCases.flatMap((item) => item.evidence).map((item) => [item.id, item]));
    const outcomes = { confirmed: 0, rejected: 0 };
    const dimensions: Record<string, Map<string, { confirmed: number; rejected: number }>> = {
      category: new Map(), language: new Map(), media_type: new Map(), review_reason: new Map(),
    };
    const mediaKind = (mime: string | undefined) => mime?.startsWith("image/") ? "image" : mime === "application/pdf" ? "pdf" : mime?.startsWith("video/") ? "video" : mime?.startsWith("audio/") ? "audio" : mime?.startsWith("text/") ? "text" : "other";
    for (const flag of demoFlags) {
      if (flag.review_status !== "confirmed" && flag.review_status !== "rejected") continue;
      const evidence = evidenceById.get(flag.evidence_id);
      outcomes[flag.review_status] += 1;
      const labels = {
        category: flag.threat_class.toLowerCase(),
        language: "unknown",
        media_type: mediaKind(evidence?.mime_type),
        review_reason: flag.review_reason || "not_recorded",
      };
      for (const [dimension, label] of Object.entries(labels)) {
        const counts = dimensions[dimension].get(label) || { confirmed: 0, rejected: 0 };
        counts[flag.review_status] += 1;
        dimensions[dimension].set(label, counts);
      }
    }
    const buckets = (dimension: string) => [...dimensions[dimension].entries()].sort(([a], [b]) => a.localeCompare(b)).map(([label, counts]) => ({ ...counts, label, total: counts.confirmed + counts.rejected }));
    return {
      source: "human_review_feedback", reviewed_flag_count: outcomes.confirmed + outcomes.rejected, outcomes,
      by_category: buckets("category"), by_language: buckets("language"), by_media_type: buckets("media_type"), by_review_reason: buckets("review_reason"),
      training_enabled: false,
      limitations: [
        "These are counts for AI flags that a reviewer confirmed or rejected; they are not accuracy, precision, recall, or false-positive rates.",
        "Evidence without a generated flag is excluded, so missed threats cannot be counted here.",
        "Reviews may not be independently adjudicated and should not be treated as representative of all cases.",
        "This feedback is not used to train or update the analysis model.",
      ],
    };
  }
  return request<ReviewInsights>("/ai/review-insights");
}

export async function getAudit(caseId?: string): Promise<AuditEntry[]> {
  if (MOCK) return demoAudit.filter((entry) => !caseId || entry.case_id === caseId).map((entry) => ({ ...entry }));
  const query = caseId ? `?case_id=${encodeURIComponent(caseId)}` : "";
  const data = await request<AuditEntry[] | { items: AuditEntry[] }>(`/audit${query}`);
  return Array.isArray(data) ? data : data.items;
}

export async function verifyAudit(): Promise<{ valid: boolean; entries_checked: number; failed_entry_id?: string | null }> {
  if (MOCK) return { valid: true, entries_checked: demoAudit.length };
  return request("/audit/verify");
}

export async function getManagedUsers(): Promise<User[]> {
  if (MOCK) return demoUsers.map((user) => ({ ...user }));
  return request<User[]>("/admin/users");
}

export async function updateManagedUser(id: string, changes: { role?: Role; is_active?: boolean }): Promise<User> {
  if (MOCK) {
    const user = demoUsers.find((item) => item.id === id);
    if (!user) throw new ApiError("User not found.", 404);
    Object.assign(user, changes);
    return { ...user };
  }
  return request<User>(`/admin/users/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(changes) });
}

function escapePdf(value: string) {
  return value.normalize("NFKD").replace(/[^\x20-\x7E]/g, "?").replaceAll("\\", "\\\\").replaceAll("(", "\\(").replaceAll(")", "\\)");
}

function makeMockPdf(lines: string[]) {
  const content = ["BT", "/F1 10 Tf", "48 790 Td", ...lines.flatMap((line, index) => index === 0 ? [`(${escapePdf(line)}) Tj`] : ["0 -20 Td", `(${escapePdf(line)}) Tj`]), "ET"].join("\n");
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${new TextEncoder().encode(content).length} >>\nstream\n${content}\nendstream`,
  ];
  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  objects.forEach((object, index) => { offsets.push(new TextEncoder().encode(pdf).length); pdf += `${index + 1} 0 obj\n${object}\nendobj\n`; });
  const xref = new TextEncoder().encode(pdf).length;
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n${offsets.slice(1).map((offset) => `${String(offset).padStart(10, "0")} 00000 n \n`).join("")}trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return new Blob([pdf], { type: "application/pdf" });
}

export async function downloadReport(caseId: string, caseRef: string): Promise<void> {
  let blob: Blob;
  if (MOCK) {
    const item = await getCase(caseId);
    blob = makeMockPdf([
      "DigitalWitness case report - MOCK DATA",
      `Case ${item.case_ref}: ${item.title}`,
      `Generated ${new Date().toISOString()} (UTC)`,
      `Evidence records: ${item.evidence.length}`,
      ...item.evidence.flatMap((evidence) => [`${evidence.filename} | SHA-256 ${evidence.sha256}`, `Status ${evidence.status} | Verification ${evidence.verification} | Anchor ${evidence.tx_hash || "not available"}`]),
      "Audit chain check: demo result only",
      "A Verified result means unchanged since anchoring. It does not establish who created the file or whether its contents are accurate.",
      "Synthetic data only. This mock report is not an official record.",
    ]);
  } else {
    const token = getAccessToken();
    const headers = new Headers({ Accept: "application/pdf" });
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const response = await fetch(`${API_URL}/cases/${encodeURIComponent(caseId)}/report`, { headers, cache: "no-store" });
    if (!response.ok) throw new ApiError(response.status === 404 ? "The PDF report endpoint is not connected yet." : `Could not generate report (${response.status}).`, response.status);
    blob = await response.blob();
  }
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${caseRef}-report.pdf`;
  anchor.click();
  URL.revokeObjectURL(url);
}
