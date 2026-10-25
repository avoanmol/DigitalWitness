import type { CaseStatus, Severity } from "@/lib/types";
import { severityLabels, statusLabels } from "@/lib/labels";

const base = "inline-block rounded-full px-2.5 py-1 text-xs font-medium";

const statusTone: Record<CaseStatus, string> = {
  open: "bg-accent/10 text-accent",
  under_review: "bg-card text-ink",
  closed: "bg-line text-muted",
};

const severityTone: Record<Severity, string> = {
  low: "bg-card text-muted",
  medium: "bg-amber-100 text-amber-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

export function StatusPill({ status }: { status: CaseStatus }) {
  return <span className={`${base} ${statusTone[status]}`}>{statusLabels[status]}</span>;
}

export function SeverityPill({ severity }: { severity: Severity }) {
  return <span className={`${base} ${severityTone[severity]}`}>{severityLabels[severity]}</span>;
}