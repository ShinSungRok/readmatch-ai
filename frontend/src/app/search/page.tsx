import { EmptyState } from "@/components/EmptyState";
import { SearchForm } from "@/components/SearchForm";
import { SearchResults } from "@/components/SearchResults";
import { searchBooks } from "@/lib/api";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  const query = (q ?? "").trim();
  // ApiError (a non-2xx response, e.g. the backend being unreachable)
  // intentionally isn't caught here -- it propagates to the existing
  // app/error.tsx boundary, exactly like the Home page's own getHomeFeed
  // call already does.
  const results = query ? await searchBooks(query) : null;

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Search</h1>
        <SearchForm initialQuery={query} />
      </div>

      {!query ? (
        <EmptyState message="Type a title, author, or category to search." />
      ) : results && results.items.length === 0 ? (
        <EmptyState message={`No books found for "${query}".`} />
      ) : results ? (
        <SearchResults items={results.items} />
      ) : null}
    </div>
  );
}
