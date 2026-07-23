# ReadMatch AI — Frontend

The Next.js (App Router, TypeScript, Tailwind CSS) web experience for
ReadMatch AI's recommendation platform. Talks to the FastAPI backend in
`../src/readmatch_ai` over HTTP; no server-side framework/database of its
own.

## Getting started

The whole stack (Postgres + backend + this frontend) runs with one
command from the repository root — see the root
[README's Docker Compose section](../README.md#run-everything-with-docker-compose-recommended).

To run just the frontend manually instead, the backend must be running
first (from the repository root):

```bash
uvicorn readmatch_ai.api.main:app --reload
```

Then, from this directory:

```bash
npm install
npm run dev
```

Open the printed local URL (`http://localhost:3000` unless that port is
already in use). By default the frontend talks to the backend at
`http://localhost:8000`; copy `.env.example` to `.env.local` and set
`NEXT_PUBLIC_API_BASE_URL` to point elsewhere. (Under Docker Compose, an
additional server-only `API_BASE_URL_INTERNAL` variable is used instead
for server-rendered fetches — see the root `.env.example`.)

## Validation

```bash
npm run lint
npx tsc --noEmit
npm run build
```

## Layout

- `src/app` — routes (App Router): `/` (Home), `/search`, `/books/[id]`
  (Book Detail), `/library` (My Library), `/preferences` (My Preferences),
  plus the root `layout.tsx`/`loading.tsx`/`error.tsx`/`not-found.tsx` and
  `search/loading.tsx` route-level states.
- `src/components` — shared UI, notably:
  - `Header`/`Footer` — site chrome.
  - `Hero`/`RecommendationRow`/`BookCard`/`SearchResultCard` — recommendation
    and search result presentation.
  - `PersonalizedForYou` — Home's personalized recommendation row
    (`GET /recommendations/personalized/{user_id}/explained`).
  - `RecommendationReason` — renders a recommendation's evidence-based
    reasons as chips (falls back to a generic per-source label when none
    are given).
  - `FeedbackControls` — like/dislike/bookmark/read/rating controls,
    backed by `InteractionProvider`'s shared state.
  - `InteractionProvider` — the anonymous user id + shared interaction
    state (Context), consumed by every book-interaction control.
  - `OnboardingCategoryPicker` — first-visit category-interest onboarding
    card (`POST /preference-signals`).
  - `RecordBookView` — records a `view` interaction on Book Detail mount.
  - `LoadingState`/`ErrorState`/`EmptyState` — the reusable state
    primitives used across every page.
- `src/lib/api.ts` — the backend API client (typed `fetch` wrappers).
- `src/lib/config.ts` — environment-based API configuration.
- `src/lib/anonymousUser.ts` — the `localStorage`-backed anonymous user id
  (not authentication — see the file's own docstring).
