/**
 * Human-readable label for a recommendation's `source` field, or (Sprint 45)
 * a personal-library item's `interaction_type`.
 *
 * The recommendation values (POPULARITY_SOURCE/SEMANTIC_SOURCE/ALS_SOURCE/
 * HYBRID_SOURCE) mirror readmatch_ai.domain.recommendation exactly; the
 * interaction values mirror readmatch_ai.domain.interaction.InteractionType
 * exactly -- this only translates an existing, real signal into copy, never
 * invents a reason the backend didn't report.
 */
const REASON_LABELS: Record<string, string> = {
  popularity: "Popular with readers",
  semantic: "Similar to this book",
  als: "Liked by similar readers",
  hybrid: "Blended recommendation",
  like: "You liked this",
  dislike: "You disliked this",
  bookmark: "Bookmarked",
  read: "You've read this",
  rating: "You rated this",
};

export function recommendationReason(source: string): string {
  return REASON_LABELS[source] ?? source;
}
