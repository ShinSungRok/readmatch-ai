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

/** Mirrors readmatch_ai.api.schemas.BookSearchResponse (Sprint 71). */
export interface BookSearchResult {
  items: BookPresentation[];
}

/** Mirrors readmatch_ai.domain.interaction.InteractionType exactly. */
export type InteractionType = "click" | "like" | "dislike" | "bookmark" | "read" | "rating";

/** Mirrors readmatch_ai.api.schemas.InteractionResponse (Sprint 44). */
export interface Interaction {
  user_id: string;
  book_id: string;
  interaction_type: InteractionType;
  value: number | null;
}

/** Mirrors readmatch_ai.api.schemas.LibraryItemResponse (Sprint 45). */
export interface LibraryItem {
  book: BookPresentation;
  interaction_type: InteractionType;
  value: number | null;
}

export interface LibrarySection {
  id: string;
  title: string;
  items: LibraryItem[];
}

export interface PersonalLibrary {
  sections: LibrarySection[];
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

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, { cache: "no-store", ...init });
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

/**
 * GET /books/search -- see readmatch_ai.api.book_router.
 *
 * A blank query returns `items: []` (never an error) -- the backend's own
 * policy, not re-implemented here; callers may pass an untrimmed/empty
 * string safely.
 */
export function searchBooks(query: string, limit = 24): Promise<BookSearchResult> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return apiFetch<BookSearchResult>(`/books/search?${params}`);
}

/**
 * GET /library/{user_id} -- see readmatch_ai.api.library_router.
 *
 * Composed entirely by the backend (Sprint 45); an unknown-but-well-formed
 * user id (e.g. a brand new anonymous browser id) returns an empty library
 * (`sections: []`), not an error.
 */
export function getPersonalLibrary(userId: string): Promise<PersonalLibrary> {
  return apiFetch<PersonalLibrary>(`/library/${encodeURIComponent(userId)}`);
}

/**
 * POST /interactions -- see readmatch_ai.api.interaction_router.
 *
 * Recording a state-like interaction (everything but `click`) again for
 * the same user/book replaces any prior value -- idempotent, not additive.
 * Throws ApiError (404) if the book id doesn't exist, or (400) for a
 * malformed id, an unknown type, or an invalid rating value.
 */
export function recordInteraction(
  userId: string,
  bookId: string,
  interactionType: InteractionType,
  value?: number,
): Promise<Interaction> {
  return apiFetch<Interaction>("/interactions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      book_id: bookId,
      interaction_type: interactionType,
      value: value ?? null,
    }),
  });
}

/**
 * DELETE /interactions -- see readmatch_ai.api.interaction_router.
 *
 * Removes a previously recorded state-like interaction (e.g. un-bookmark).
 * A no-op if nothing was recorded -- safe to call repeatedly.
 */
export async function clearInteraction(
  userId: string,
  bookId: string,
  interactionType: InteractionType,
): Promise<void> {
  const params = new URLSearchParams({
    user_id: userId,
    book_id: bookId,
    interaction_type: interactionType,
  });
  const response = await fetch(`${getApiBaseUrl()}/interactions?${params}`, {
    method: "DELETE",
    cache: "no-store",
  });
  if (!response.ok) {
    throw new ApiError(response.status, `DELETE /interactions responded with HTTP ${response.status}`);
  }
}
