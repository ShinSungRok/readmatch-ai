import type { BookPresentation } from "@/lib/api";
import { SearchResultCard } from "@/components/SearchResultCard";

export function SearchResults({ items }: { items: BookPresentation[] }) {
  return (
    <ul className="grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      {items.map((book) => (
        <li key={book.id}>
          <SearchResultCard book={book} />
        </li>
      ))}
    </ul>
  );
}
