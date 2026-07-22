import { recommendationReason } from "@/lib/recommendationReason";

export function RecommendationReason({ source }: { source: string }) {
  return (
    <span className="inline-flex w-fit items-center rounded-full bg-black/5 px-2.5 py-0.5 text-xs text-zinc-600 dark:bg-white/10 dark:text-zinc-300">
      {recommendationReason(source)}
    </span>
  );
}
