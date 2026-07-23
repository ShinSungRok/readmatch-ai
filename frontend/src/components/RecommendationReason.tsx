import type { ExplanationReason } from "@/lib/api";
import { recommendationReason } from "@/lib/recommendationReason";

/**
 * Shows the real, evidence-based reasons from
 * GET /recommendations/personalized/{user_id}/explained when present
 * (never fabricated); otherwise falls back to the existing generic
 * per-`source` label, unchanged for every other caller.
 */
export function RecommendationReason({
  source,
  reasons,
}: {
  source: string;
  reasons?: ExplanationReason[];
}) {
  const label =
    reasons && reasons.length > 0
      ? reasons.map((reason) => reason.message).join(" · ")
      : recommendationReason(source);
  return (
    <span className="inline-flex w-fit items-center rounded-full bg-black/5 px-2.5 py-0.5 text-xs text-zinc-600 dark:bg-white/10 dark:text-zinc-300">
      {label}
    </span>
  );
}
