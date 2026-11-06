
type Props = {
  busy: boolean;
  onConfirm: () => void;
  onReject: () => void;
};

export default function ReviewButtons({
  busy,
  onConfirm,
  onReject,
}: Props) {
  const base =
    "border px-4 py-2 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-40";

  return (
    <div className="flex flex-wrap gap-2">
      <button
        type="button"
        disabled={busy}
        onClick={onConfirm}
        className={`${base} border-[#242424] bg-[#242424] text-white hover:bg-[#AD841E] hover:border-[#AD841E]`}
      >
        {busy ? "Saving..." : "Confirm finding"}
      </button>

      <button
        type="button"
        disabled={busy}
        onClick={onReject}
        className={`${base} border-[#D8D5CD] text-[#555] hover:border-[#242424] hover:text-[#242424]`}
      >
        Reject
      </button>
    </div>
  );
}
