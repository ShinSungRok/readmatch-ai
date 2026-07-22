"use client";

import { useState } from "react";

/** A generic, always-available fallback -- used only when a real cover_url
 * (e.g. a Data4Library image) fails to load client-side. The backend
 * already guarantees cover_url is never empty (see
 * readmatch_ai.application.book_presentation.deterministic_cover_fallback),
 * so this only covers a broken/unreachable external URL, not a missing one.
 */
const FALLBACK_COVER_SRC = "/covers/placeholder-0.svg";

export function BookCover({ coverUrl }: { coverUrl: string }) {
  const [src, setSrc] = useState(coverUrl);
  return (
    <img
      src={src}
      alt=""
      aria-hidden
      className="h-full w-full object-cover"
      onError={() => {
        if (src !== FALLBACK_COVER_SRC) {
          setSrc(FALLBACK_COVER_SRC);
        }
      }}
    />
  );
}
