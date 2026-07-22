/**
 * Human-readable label for a recommendation's `source` field.
 *
 * Every value here (POPULARITY_SOURCE/SEMANTIC_SOURCE/ALS_SOURCE/HYBRID_SOURCE)
 * mirrors readmatch_ai.domain.recommendation exactly -- this only translates
 * an existing, real signal into copy, never invents a reason the backend
 * didn't report.
 */
const REASON_LABELS: Record<string, string> = {
  popularity: "Popular with readers",
  semantic: "Similar to this book",
  als: "Liked by similar readers",
  hybrid: "Blended recommendation",
};

export function recommendationReason(source: string): string {
  return REASON_LABELS[source] ?? source;
}
