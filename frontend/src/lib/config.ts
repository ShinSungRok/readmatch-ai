const DEFAULT_API_BASE_URL = "http://localhost:8000";

/** The backend API's base URL, resolved from the environment.
 *
 * `NEXT_PUBLIC_*` variables are inlined at build time and readable in the
 * browser, which is required here since client components fetch the
 * backend directly. Defaults to the backend's own documented local dev
 * address so a fresh checkout works without any `.env` file.
 *
 * Server-rendered code (Server Components, running inside this app's own
 * container under Docker Compose) reaches the backend through a
 * *different* address than the browser does: `API_BASE_URL_INTERNAL`
 * (server-only, never sent to the browser -- no `NEXT_PUBLIC_` prefix),
 * set to the backend's Docker Compose service name, e.g.
 * `http://backend:8000` -- "localhost" inside this container is this
 * container, not the backend's. Outside Docker (e.g. `npm run dev`
 * against a manually-started backend) `API_BASE_URL_INTERNAL` is unset,
 * so server and client resolve to the exact same `NEXT_PUBLIC_API_BASE_URL`
 * -- this function's behavior is then identical to before this
 * distinction existed.
 */
export function getApiBaseUrl(): string {
  if (typeof window === "undefined" && process.env.API_BASE_URL_INTERNAL) {
    return process.env.API_BASE_URL_INTERNAL;
  }
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL;
}
