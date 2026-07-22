import { getApiBaseUrl } from "@/lib/config";

/** Mirrors readmatch_ai.api.schemas.BookPresentationResponse (Sprint 39/42). */
export interface BookPresentation {
  id: string;
  isbn: string;
  title: string;
  author: string;
  category: string;
  publisher: string | null;
  description: string | null;
  cover_url: string;
  published_date: string | null;
}

export interface HomeFeedItem {
  book: BookPresentation;
  score: number;
  source: string;
}

export interface HomeFeedSection {
  id: string;
  title: string;
  items: HomeFeedItem[];
}

export interface HomeFeed {
  hero: HomeFeedItem | null;
  sections: HomeFeedSection[];
}

/** Mirrors readmatch_ai.api.schemas.BookDetailResponse (Sprint 43). */
export interface BookDetail {
  book: BookPresentation;
  similar_books: HomeFeedItem[];
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

/**
 * GET /home-feed -- see readmatch_ai.api.home_feed_router.
 *
 * The one consolidated call the recommendation home page needs: a hero plus
 * zero or more titled sections, already composed and presentation-enriched
 * by the backend (Sprint 42) -- the frontend does no further recommendation
 * composition of its own.
 */
export function getHomeFeed(limit = 12): Promise<HomeFeed> {
  return apiFetch<HomeFeed>(`/home-feed?limit=${limit}`);
}

/**
 * GET /books/{book_id} -- see readmatch_ai.api.book_router.
 *
 * Returns `null` for a well-formed but unknown book id (the backend's 404),
 * so the caller can render a proper not-found page instead of the generic
 * error boundary. Any other non-2xx status still throws ApiError.
 */
export async function getBookDetail(bookId: string): Promise<BookDetail | null> {
  const response = await fetch(`${getApiBaseUrl()}/books/${encodeURIComponent(bookId)}`, {
    cache: "no-store",
  });
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new ApiError(response.status, `/books/${bookId} responded with HTTP ${response.status}`);
  }
  return (await response.json()) as BookDetail;
}
