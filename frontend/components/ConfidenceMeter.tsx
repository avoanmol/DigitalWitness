
export default function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  const weak = value < 0.4;

  return (
    <div className="flex items-center gap-3 text-xs text-[#666666]">
      <div
        className="h-[3px] w-20 overflow-hidden bg-[#E5E2DB]"
        role="progressbar"
        aria-label="Analysis confidence"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full bg-[#AD841E] transition-[width] duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>

      <span className="tabular-nums">{pct}% confidence</span>

      {weak && (
        <span className="text-[#9A7020]">· Weak signal</span>
      )}
    </div>
  );
}
