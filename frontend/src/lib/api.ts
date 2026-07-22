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
