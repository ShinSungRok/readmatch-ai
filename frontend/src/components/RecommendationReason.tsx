import type { ExplanationReason } from "@/lib/api";
import { recommendationReason } from "@/lib/recommendationReason";

/** A card is only ~160-176px wide -- more than this many reasons stacked as
 * chips would dominate it, so only the most-significant ones are shown. */
const MAX_VISIBLE_REASONS = 2;

/**
 * Display priority, most-significant first -- deliberately *not* the
 * backend's own canonical order (popularity/semantic_similarity/
 * collaborative_behavior/novelty/diversity, profile-based reasons always
 * appended last). With `MAX_VISIBLE_REASONS` capping what's shown, using
 * that order as-is would mean a book's two most generic reasons
 * (popularity/novelty appear on nearly every item) crowd out the specific,
 * personalized ones this Sprint's own profile work exists to surface --
 * this reorders only *which* already-real reasons are picked to display,
 * never their text or whether the backend reported them.
 */
const REASON_DISPLAY_PRIORITY = [
  "favorite_author",
  "favorite_category",
  "recent_search_match",
  "collaborative_behavior",
  "semantic_similarity",
  "novelty",
  "popularity",
  "diversity",
];

const chipClassName =
  "inline-flex w-fit items-center rounded-full bg-black/5 px-2.5 py-0.5 text-xs text-zinc-600 dark:bg-white/10 dark:text-zinc-300";

function mostSignificant(reasons: ExplanationReason[]): ExplanationReason[] {
  return [...reasons]
    .sort((a, b) => REASON_DISPLAY_PRIORITY.indexOf(a.type) - REASON_DISPLAY_PRIORITY.indexOf(b.type))
    .slice(0, MAX_VISIBLE_REASONS);
}

/**
 * Shows the real, evidence-based reasons from
 * GET /recommendations/personalized/{user_id}/explained when present
 * (never fabricated); otherwise falls back to the existing generic
 * per-`source` label, unchanged for every other caller.
 *
 * Each reason renders as its own chip (wrapping via flex-wrap) rather than
 * one string joined into a single pill -- a single `rounded-full` badge
 * holding several concatenated sentences stretched across multiple lines
 * loses its pill shape and reads as one run-on sentence.
 */
export function RecommendationReason({
  source,
  reasons,
}: {
  source: string;
  reasons?: ExplanationReason[];
}) {
  if (!reasons || reasons.length === 0) {
    return <span className={chipClassName}>{recommendationReason(source)}</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {mostSignificant(reasons).map((reason) => (
        <span key={reason.type} className={chipClassName}>
          {reason.message}
        </span>
      ))}
    </div>
  );
}
