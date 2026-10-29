import type { VerificationResult } from "@/lib/types";

const config: Record<VerificationResult, { title: string; caption: string; icon: string }> = {
  verified: { title: "Verified", caption: "Unchanged since anchoring", icon: "✓" },
  altered: { title: "Altered", caption: "Hash differs from the recorded value", icon: "!" },
  pending: { title: "Pending anchor", caption: "Not anchored yet", icon: "◷" },
  not_checked: { title: "Not checked", caption: "Anchored; run an integrity check", icon: "○" },
  error: { title: "Check unavailable", caption: "Verification could not complete", icon: "×" },
};

export function VerifyBadge({ result, compact = false }: { result: VerificationResult | null | undefined; compact?: boolean }) {
  const item = config[result || "pending"];
  return <span className={`verify-badge verify-${result || "pending"} ${compact ? "verify-compact" : ""}`} title={item.caption}>
    <span className="verify-icon" aria-hidden="true">{item.icon}</span>
    <span><strong>{item.title}</strong>{!compact && <small>{item.caption}</small>}</span>
  </span>;
}
