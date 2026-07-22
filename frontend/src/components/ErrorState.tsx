export function ErrorState({
  message = "Something went wrong while talking to the backend.",
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-3 rounded-lg border border-red-300 bg-red-50 p-6 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200"
    >
      <p>{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-full border border-current px-4 py-1.5 text-sm font-medium hover:bg-red-100 dark:hover:bg-red-900"
        >
          Try again
        </button>
      ) : null}
    </div>
  );
}
