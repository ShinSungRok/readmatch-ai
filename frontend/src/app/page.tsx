import { EmptyState } from "@/components/EmptyState";
import { getHealth, getPopularityRecommendations } from "@/lib/api";

export default async function HomePage() {
  const [health, recommendations] = await Promise.all([
    getHealth(),
    getPopularityRecommendations(6),
  ]);

  return (
    <div className="flex flex-col gap-10">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight">ReadMatch AI</h1>
        <p className="mt-2 text-zinc-600 dark:text-zinc-400">
          A hybrid book recommendation experience.
        </p>
        <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-black/10 px-3 py-1 text-sm dark:border-white/15">
          <span
            aria-hidden
            className={`h-2 w-2 rounded-full ${health.healthy ? "bg-green-500" : "bg-red-500"}`}
          />
          Backend {health.healthy ? "connected" : "unavailable"}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold tracking-tight">Popular books</h2>
        {recommendations.items.length === 0 ? (
          <div className="mt-4">
            <EmptyState message="No books have been registered yet." />
          </div>
        ) : (
          <ul className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-6">
            {recommendations.items.map((item) => (
              <li
                key={item.book.id}
                className="rounded-lg border border-black/10 p-3 text-sm dark:border-white/15"
              >
                <p className="font-medium">{item.book.title}</p>
                <p className="text-zinc-500 dark:text-zinc-400">{item.book.author}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
