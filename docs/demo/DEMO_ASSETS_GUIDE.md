# Demo Assets Guide

How to capture the portfolio screenshots/GIFs for ReadMatch AI's five core
screens. No screenshot/GIF files are committed to this repository — this
environment has no browser automation available to produce them (see
`docs/release/RELEASE_CANDIDATE.md`'s Known Limitations), so this document
is the reproducible recipe instead, kept next to the code so it stays
accurate as the UI evolves. Once captured, drop the files under
`docs/demo/screenshots/` (create it) using the filenames below and link
them from README's [Demo](../../README.md#demo) section.

## Prerequisites

Follow the README's [Quick Start](../../README.md#quick-start) through
[Seed demo data](../../README.md#seed-demo-data) and
[Run the frontend](../../README.md#run-the-frontend) — a real PostgreSQL +
pgvector backend, seeded with the real Data4Library sample data, plus
`next dev` on `http://localhost:3000`.

Use a fresh anonymous browser session for the first three screenshots
(a private/incognito window, or clear `localStorage` for `localhost:3000`)
so the onboarding card and cold-start states are genuinely reproduced, not
faked. Recommended viewport: **1440×900** for desktop screenshots (matches
the `lg:` Tailwind breakpoint used throughout, so recommendation rows show
their full multi-card layout), plus one **390×844** (iPhone-sized) capture
of Home to demonstrate the responsive layout.

## Screenshots

For each, capture the full viewport (not just the visible fold) where
noted, using your browser's built-in full-page screenshot capability
(Firefox: right-click → "Take Screenshot" → "Save full page"; Chrome
DevTools: Cmd/Ctrl+Shift+P → "Capture full size screenshot").

1. **`home-onboarding.png`** — `http://localhost:3000/`, fresh session,
   before dismissing the onboarding card. Shows the "선호하는 카테고리를
   선택해 주세요" category picker and the Hero below it.
2. **`home-personalized.png`** — same session, after picking 2-3
   categories and clicking "선호도 저장" (the card switches to a summary
   of your picks with a "초기화" button), then liking/bookmarking a
   book from the Hero or a recommendation row. Scroll so the **"For You"**
   row (with its real evidence-based reason chips — not the "Not enough
   activity yet" cold-start note) is in frame, alongside at least one
   Popularity/Hybrid/Semantic row below it.
3. **`search-results.png`** — `http://localhost:3000/search?q=한강` (or
   any seeded author/title) — the search input pre-filled, and the result
   grid below it.
4. **`book-detail.png`** — click through to any book's detail page. Shows
   the cover, metadata, the Like/Bookmark/Read/Rate `FeedbackControls`
   row, and the "Similar books" row.
5. **`my-preferences.png`** — `http://localhost:3000/preferences`, **after**
   step 2's activity — shows the like/dislike stat tiles and the
   Favorite categories/Favorite authors/Recent interests/Recent searches
   tag lists actually populated (not the empty state).

## GIF: the personalization loop

One GIF is more convincing than any static screenshot for this project's
actual thesis (behavior → visibly different recommendations) — capture the
**before/after** difference in a single continuous recording rather than
stitching two screenshots:

1. Start recording (see tool options below) on `http://localhost:3000/`
   with a **fresh** anonymous session — frame the "For You" row showing
   its cold-start note.
2. Click into a book, like it (or bookmark/rate it ≥4), navigate back to
   Home.
3. Let the "For You" row visibly re-fetch (no reload needed — it updates
   in place) and show its reason chip change from generic
   ("Popular with many readers.") to personalized
   ("By `<author>`, one of your favorite authors." or similar).
4. Stop recording. Target 10-15 seconds, trimmed to just the meaningful
   moment (a longer raw capture is fine — trim on export).
5. Save as `personalization-loop.gif` under `docs/demo/screenshots/`.

**Tool options** (any produce an equivalent result — pick whichever is
already installed, no new project dependency either way):

- **macOS**: QuickTime Player's "New Screen Recording" → export as `.mov`
  → convert with `gifski` (`brew install gifski`):
  `gifski --fps 12 --width 960 -o personalization-loop.gif recording.mov`.
- **Linux**: [Peek](https://github.com/phw/peek) (`apt install peek` or
  equivalent) records directly to `.gif`.
- **Windows**: [ScreenToGif](https://www.screentogif.com/) records
  directly to `.gif`.
- **Any OS, no extra install**: record with the browser DevTools'
  built-in screen recorder (Chrome/Edge "Recorder" panel under DevTools
  → More tools), export as video, then convert with `ffmpeg` (already a
  common local dependency):
  `ffmpeg -i recording.webm -vf "fps=12,scale=960:-1" personalization-loop.gif`.

Keep the GIF under a few MB (12 fps / ≤960px wide is usually enough for a
README preview) so it loads quickly wherever it's embedded.

## Embedding in README

Once files exist under `docs/demo/screenshots/`, add them to README's
[Demo](../../README.md#demo) section, e.g.:

```markdown
![Home with personalized "For You" row](docs/demo/screenshots/home-personalized.png)
![The personalization loop: like a book, see recommendations and reasons change](docs/demo/screenshots/personalization-loop.gif)
```

Do not commit large binary assets casually — screenshots/GIFs are a
one-time, deliberate addition; re-capture and replace rather than
accumulating stale ones as the UI changes.
