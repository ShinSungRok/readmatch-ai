import { notFound } from "next/navigation";
import { BookCover } from "@/components/BookCover";
import { FeedbackControls } from "@/components/FeedbackControls";
import { RecommendationRow } from "@/components/RecommendationRow";
import { RecordBookView } from "@/components/RecordBookView";
import { getBookDetail } from "@/lib/api";

export default async function BookDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const detail = await getBookDetail(id);
  if (!detail) {
    notFound();
  }
  const { book, similar_books } = detail;

  return (
    <div className="flex flex-col gap-10">
      <RecordBookView bookId={book.id} />
      <section className="flex flex-col gap-6 sm:flex-row">
        <div className="aspect-[2/3] w-full flex-none overflow-hidden rounded-lg border border-black/10 sm:w-64 dark:border-white/15">
          <BookCover key={book.cover_url} coverUrl={book.cover_url} />
        </div>
        <div className="flex flex-col gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">{book.title}</h1>
          <p className="text-zinc-600 dark:text-zinc-400">
            {book.author} &middot; {book.category}
          </p>
          {book.publisher || book.published_date ? (
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              {[book.publisher, book.published_date].filter(Boolean).join(" · ")}
            </p>
          ) : null}
          <p className="text-xs text-zinc-400 dark:text-zinc-500">ISBN {book.isbn}</p>
          {book.description ? (
            <p className="text-zinc-700 dark:text-zinc-300">{book.description}</p>
          ) : null}
          <FeedbackControls bookId={book.id} />
        </div>
      </section>

      <RecommendationRow title="Similar books" items={similar_books} />
    </div>
  );
}
