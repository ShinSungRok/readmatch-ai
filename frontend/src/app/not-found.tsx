import Link from "next/link";
import { EmptyState } from "@/components/EmptyState";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center gap-4">
      <EmptyState message="We couldn't find that page or book." />
      <Link href="/" className="text-sm underline">
        Back to home
      </Link>
    </div>
  );
}
