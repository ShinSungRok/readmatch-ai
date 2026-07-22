"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { RecommendationRow } from "@/components/RecommendationRow";
import { getPersonalLibrary, type PersonalLibrary } from "@/lib/api";
import { getOrCreateAnonymousUserId } from "@/lib/anonymousUser";

type LoadState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; library: PersonalLibrary };

export default function LibraryPage() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  const fetchLibrary = useCallback(() => {
    const userId = getOrCreateAnonymousUserId();
    getPersonalLibrary(userId)
      .then((library) => setState({ status: "ready", library }))
      .catch(() => setState({ status: "error" }));
  }, []);

  useEffect(() => {
    fetchLibrary();
  }, [fetchLibrary]);

  const retry = useCallback(() => {
    setState({ status: "loading" });
    fetchLibrary();
  }, [fetchLibrary]);

  if (state.status === "loading") {
    return <LoadingState label="Loading your library..." />;
  }

  if (state.status === "error") {
    return <ErrorState message="We couldn't load your library." onRetry={retry} />;
  }

  if (state.library.sections.length === 0) {
    return (
      <EmptyState message="Your library is empty. Like, bookmark, or rate a book to see it here." />
    );
  }

  return (
    <div className="flex flex-col gap-10">
      <h1 className="text-2xl font-semibold tracking-tight">My Library</h1>
      {state.library.sections.map((section) => (
        <RecommendationRow
          key={section.id}
          title={section.title}
          items={section.items.map((item) => ({
            book: item.book,
            score: item.value ?? 0,
            source: item.interaction_type,
          }))}
        />
      ))}
    </div>
  );
}
