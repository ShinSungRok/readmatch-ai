import { getApiBaseUrl } from "@/lib/config";

export interface Book {
  id: string;
  isbn: string;
  title: string;
  author: string;
  category: string;
}

export interface RecommendationItem {
  book: Book;
  score: number;
  source: string;
}

export interface RecommendationResponse {
  items: RecommendationItem[];
}

export interface ComponentCheck {
  name: string;
  available: boolean;
  detail: string | null;
}

export interface HealthResponse {
  healthy: boolean;
  checks: ComponentCheck[];
}

/** Raised when the backend responds, but with a non-2xx status. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new ApiError(response.status, `${path} responded with HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

/** GET /health -- see readmatch_ai.api.health_router. */
export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

/** GET /recommendations/popularity -- see readmatch_ai.api.recommendations_router. */
export function getPopularityRecommendations(limit = 10): Promise<RecommendationResponse> {
  return apiFetch<RecommendationResponse>(`/recommendations/popularity?limit=${limit}`);
}

/**
 * GET /recommendations/hybrid -- see readmatch_ai.api.recommendations_router.
 *
 * Called with no book_id/user_id: blends popularity, semantic, and ALS
 * signals without anchoring to a specific book or (out of Phase 2's scope)
 * an authenticated user.
 */
export function getHybridRecommendations(limit = 10): Promise<RecommendationResponse> {
  return apiFetch<RecommendationResponse>(`/recommendations/hybrid?limit=${limit}`);
}

/**
 * GET /recommendations/semantic/{book_id} -- see readmatch_ai.api.recommendations_router.
 *
 * Returns an empty item list (not an error) if the source book has no
 * embedding yet -- the caller decides whether to render the section at all.
 */
export function getSemanticRecommendations(
  bookId: string,
  limit = 10,
): Promise<RecommendationResponse> {
  return apiFetch<RecommendationResponse>(
    `/recommendations/semantic/${encodeURIComponent(bookId)}?limit=${limit}`,
  );
}
