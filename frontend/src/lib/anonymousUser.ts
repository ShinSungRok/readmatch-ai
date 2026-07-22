const STORAGE_KEY = "readmatch-ai:anonymous-user-id";

/**
 * Returns a stable, per-browser anonymous user id, persisted in
 * localStorage (generated with crypto.randomUUID() the first time).
 *
 * This is not authentication: nothing is verified server-side, there is no
 * login, and no credential is issued. Phase 3 explicitly excludes
 * authentication and user sessions -- this only lets a single browser
 * demonstrate the personal library and recommendation feedback loop across
 * page loads without one. Client-only: must be called from a Client
 * Component (or an effect), since localStorage does not exist on the
 * server.
 */
export function getOrCreateAnonymousUserId(): string {
  const existing = window.localStorage.getItem(STORAGE_KEY);
  if (existing) {
    return existing;
  }
  const created = crypto.randomUUID();
  window.localStorage.setItem(STORAGE_KEY, created);
  return created;
}
