import type { CaseStatus, Severity } from "@/lib/types";
import { severityLabels, statusLabels } from "@/lib/labels";

const base =
  "inline-flex items-center border px-3 py-1 text-xs font-medium tracking-wide";

const statusTone: Record<CaseStatus, string> = {
  open: "border-[#D8C18A] bg-[#FBF7EC] text-[#8A681B]",
  under_review: "border-[#D6D6D6] bg-[#F5F5F5] text-[#555555]",
  closed: "border-[#D6D6D6] bg-white text-[#777777]",
};

const severityTone: Record<Severity, string> = {
  low: "border-[#D6D6D6] bg-white text-[#666666]",
  medium: "border-[#E5D5A8] bg-[#FBF7EC] text-[#8A681B]",
  high: "border-[#E8C5A9] bg-[#FCF3EC] text-[#995321]",
  critical: "border-[#E5BABA] bg-[#FCF0F0] text-[#A33B3B]",
};

export function StatusPill({ status }: { status: CaseStatus }) {
  return (
    <span className={`${base} ${statusTone[status]}`}>
      {statusLabels[status]}
    </span>
  );
}

export function SeverityPill({ severity }: { severity: Severity }) {
  return (
    <span className={`${base} ${severityTone[severity]}`}>
      {severityLabels[severity]}
    </span>
  );
}