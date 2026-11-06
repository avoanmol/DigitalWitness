
export default function UploadProgress({ percent }: { percent: number }) {
  const safePercent = Math.min(100, Math.max(0, percent));

  return (
    <div
      role="progressbar"
      aria-label="Upload progress"
      aria-valuenow={safePercent}
      aria-valuemin={0}
      aria-valuemax={100}
      className="h-1 w-full bg-[#E5E3DD]"
    >
      <div
        className="h-1 bg-[#AD841E] transition-[width] duration-300 ease-out"
        style={{ width: `${safePercent}%` }}
      />
    </div>
  );
}
