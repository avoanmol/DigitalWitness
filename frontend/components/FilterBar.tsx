
"use client";

import type { CaseFilters } from "@/lib/types";
import {
  severityLabels,
  statusLabels,
  threatLabels,
  verifyLabels,
} from "@/lib/labels";

export const emptyFilters: CaseFilters = {
  q: "",
  status: "",
  severity: "",
  threatClass: "",
  verification: "",
  from: "",
  to: "",
};

const input =
  "mt-2 w-full border border-[#D8D5CD] bg-white px-3 py-2.5 text-sm text-[#242424] outline-none transition focus:border-[#AD841E]";

function Select<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T | "";
  options: Record<T, string>;
  onChange: (v: T | "") => void;
}) {
  return (
    <label className="block text-xs text-[#666666]">
      {label}
      <select
        className={input}
        value={value}
        onChange={(e) => onChange(e.target.value as T | "")}
      >
        <option value="">All</option>
        {Object.entries(options).map(([key, text]) => (
          <option key={key} value={key}>
            {text as string}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function FilterBar({
  filters,
  onChange,
}: {
  filters: CaseFilters;
  onChange: (f: CaseFilters) => void;
}) {
  const set = <K extends keyof CaseFilters>(
    key: K,
    value: CaseFilters[K],
  ) => onChange({ ...filters, [key]: value });

  const dirty = JSON.stringify(filters) !== JSON.stringify(emptyFilters);

  return (
    <section className="border-y border-[#D8D5CD] py-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-[#242424]">Filter cases</h2>

        {dirty && (
          <button
            type="button"
            onClick={() => onChange(emptyFilters)}
            className="text-xs text-[#777777] underline underline-offset-4 transition hover:text-[#AD841E]"
          >
            Clear filters
          </button>
        )}
      </div>

      <div className="grid gap-x-5 gap-y-4 sm:grid-cols-2 lg:grid-cols-4">
        <label className="block text-xs text-[#666666] sm:col-span-2">
          Case ID or title
          <input
            className={input}
            placeholder="e.g. DW-2026-0003"
            value={filters.q}
            onChange={(e) => set("q", e.target.value)}
          />
        </label>

        <Select
          label="Status"
          value={filters.status}
          options={statusLabels}
          onChange={(v) => set("status", v)}
        />

        <Select
          label="Severity"
          value={filters.severity}
          options={severityLabels}
          onChange={(v) => set("severity", v)}
        />

        <Select
          label="Threat type"
          value={filters.threatClass}
          options={threatLabels}
          onChange={(v) => set("threatClass", v)}
        />

        <Select
          label="Verification"
          value={filters.verification}
          options={verifyLabels}
          onChange={(v) => set("verification", v)}
        />

        <label className="block text-xs text-[#666666]">
          From
          <input
            type="date"
            className={input}
            value={filters.from}
            onChange={(e) => set("from", e.target.value)}
          />
        </label>

        <label className="block text-xs text-[#666666]">
          To
          <input
            type="date"
            className={input}
            value={filters.to}
            onChange={(e) => set("to", e.target.value)}
          />
        </label>
      </div>
    </section>
  );
}
