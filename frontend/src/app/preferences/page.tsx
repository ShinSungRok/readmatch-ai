"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { getUserPreferenceProfile, type UserPreferenceProfile } from "@/lib/api";
import { getOrCreateAnonymousUserId } from "@/lib/anonymousUser";

type LoadState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; profile: UserPreferenceProfile };

function TagList({ label, values }: { label: string; values: string[] }) {
  if (values.length === 0) {
    return null;
  }
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-medium text-zinc-600 dark:text-zinc-400">{label}</p>
      <div className="flex flex-wrap gap-2">
        {values.map((value) => (
          <span
            key={value}
            className="rounded-full bg-black/5 px-3 py-1 text-sm dark:bg-white/10"
          >
            {value}
          </span>
        ))}
      </div>
    </div>
  );
}

function StatTile({ label, count }: { label: string; count: number }) {
  return (
    <div className="flex-1 rounded-lg border border-black/10 p-4 dark:border-white/15">
      <p className="text-2xl font-semibold tracking-tight">{count}</p>
      <p className="text-sm text-zinc-500 dark:text-zinc-400">{label}</p>
    </div>
  );
}

export default function PreferencesPage() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  const fetchProfile = useCallback(() => {
    const userId = getOrCreateAnonymousUserId();
    getUserPreferenceProfile(userId)
      .then((profile) => setState({ status: "ready", profile }))
      .catch(() => setState({ status: "error" }));
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const retry = useCallback(() => {
    setState({ status: "loading" });
    fetchProfile();
  }, [fetchProfile]);

  if (state.status === "loading") {
    return <LoadingState label="Loading your preferences..." />;
  }

  if (state.status === "error") {
    return <ErrorState message="We couldn't load your preferences." onRetry={retry} />;
  }

  const { profile } = state;
  // Every signal this profile can carry -- book counts included, unlike
  // before, when a user who had only disliked a book (no favorites/
  // interests/searches yet) would incorrectly see the cold-start message
  // with their own dislike count never shown anywhere on the page.
  const hasAnyActivity =
    profile.favorite_categories.length > 0 ||
    profile.favorite_authors.length > 0 ||
    profile.recent_interests.length > 0 ||
    profile.recent_search_terms.length > 0 ||
    profile.positive_book_count > 0 ||
    profile.negative_book_count > 0;

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">My Preferences</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Built entirely from your own activity -- likes, bookmarks, ratings, reads, views, and
          searches. See the actual books in{" "}
          <Link href="/library" className="underline underline-offset-2">
            My Library
          </Link>
          .
        </p>
      </div>

      {!hasAnyActivity ? (
        <EmptyState message="Not enough activity yet. Like, bookmark, rate, or search for a book to build your preference profile." />
      ) : (
        <div className="flex flex-col gap-8">
          <div className="flex gap-4">
            <StatTile label="Book(s) you liked" count={profile.positive_book_count} />
            <StatTile label="Book(s) you disliked" count={profile.negative_book_count} />
          </div>
          <div className="flex flex-col gap-6">
            <TagList label="Favorite categories" values={profile.favorite_categories} />
            <TagList label="Favorite authors" values={profile.favorite_authors} />
            <TagList label="Recent interests" values={profile.recent_interests} />
            <TagList label="Recent searches" values={profile.recent_search_terms} />
          </div>
        </div>
      )}
    </div>
  );
}
