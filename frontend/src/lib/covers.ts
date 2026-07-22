const PLACEHOLDER_COVER_COUNT = 6;

/**
 * A stable placeholder cover path derived only from the book id.
 *
 * Mirrors the backend's `deterministic_cover_fallback` (same book id always
 * maps to the same one of `PLACEHOLDER_COVER_COUNT` placeholder assets, in
 * `public/covers/`) so cards look consistent without any network call. The
 * backend does not yet expose `cover_url` on the recommendation endpoints
 * this page uses (that arrives with the Sprint 42 home feed), so this is
 * computed client-side for now.
 */
export function deterministicCoverFallback(bookId: string): string {
  let hash = 0;
  for (let i = 0; i < bookId.length; i += 1) {
    hash = (hash * 31 + bookId.charCodeAt(i)) | 0;
  }
  const bucket = Math.abs(hash) % PLACEHOLDER_COVER_COUNT;
  return `/covers/placeholder-${bucket}.svg`;
}
