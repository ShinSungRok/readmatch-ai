# ReadMatch AI — Frontend

The Next.js (App Router, TypeScript, Tailwind CSS) web experience for
ReadMatch AI's recommendation platform. Talks to the FastAPI backend in
`../src/readmatch_ai` over HTTP; no server-side framework/database of its
own.

## Getting started

The backend must be running first (from the repository root):

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
`NEXT_PUBLIC_API_BASE_URL` to point elsewhere.

## Validation

```bash
npm run lint
npx tsc --noEmit
npm run build
```

## Layout

- `src/app` — routes (App Router): layout, pages, and the `loading.tsx`/
  `error.tsx` route-level loading and error states.
- `src/components` — shared UI: `Header`, and the reusable `LoadingState`/
  `ErrorState`/`EmptyState` primitives used across pages.
- `src/lib/api.ts` — the backend API client (typed `fetch` wrappers).
- `src/lib/config.ts` — environment-based API configuration.
