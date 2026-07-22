const DEFAULT_API_BASE_URL = "http://localhost:8000";

/** The backend API's base URL, resolved from the environment.
 *
 * `NEXT_PUBLIC_*` variables are inlined at build time and readable in the
 * browser, which is required here since pages fetch the backend directly.
 * Defaults to the backend's own documented local dev address so a fresh
 * checkout works without any `.env` file.
 */
export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL;
}
