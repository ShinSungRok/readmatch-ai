from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.application.batch_generate_book_embeddings_use_case import (
    BatchGenerateBookEmbeddingsUseCase,
)


@dataclass(frozen=True)
class EmbeddingRefreshResult:
    """Deterministic summary of one RefreshBookEmbeddingsUseCase run.

    Mirrors BatchEmbeddingGenerationStats' own tuple-of-ids shape (stable
    equality/repr), plus `failed` for a whole-run failure (see execute()'s
    docstring) -- there is no per-book failure granularity below this,
    since BookEmbeddingGenerator.generate_batch() has no partial-failure
    contract to report through.
    """

    requested: int
    generated: tuple[str, ...]
    skipped: tuple[str, ...]
    failed: tuple[str, ...] = ()


class RefreshBookEmbeddingsUseCase:
    """Connects a synchronization run to the existing embedding pipeline.

    Reuses BatchGenerateBookEmbeddingsUseCase (Sprint 50) exactly as it
    already exists -- no new regeneration-decision logic, no duplicate
    embedding engine. That use case already regenerates only for books
    that are new, have no stored embedding, have changed canonical content
    (via the existing content-hash rule), or whose stored embedding's
    (model_name, model_version) is stale relative to the currently
    configured generator; every other book is skipped, with zero model
    calls. Since staleness (a model/version bump) can affect *any* book in
    the catalog, not just ones a particular sync run touched, this always
    re-evaluates the whole catalog -- exactly what BatchGenerateBookEmbeddingsUseCase
    already does -- rather than being scoped to a narrower "just-synced"
    book list.

    If the underlying batch call raises (e.g. a real model/library failure
    -- DeterministicFakeBookEmbeddingGenerator, the default, never raises),
    that failure is caught here and reported via `failed` instead of
    propagating, so one failing embedding-refresh stage does not abort a
    caller's larger orchestration pipeline (see
    application.refresh_recommendation_data_use_case, Sprint 60) -- the
    same "one stage's failure is reported, not fatal to the whole run"
    principle ImportBooksUseCase already applies per-record.
    """

    def __init__(
        self, batch_generate_book_embeddings_use_case: BatchGenerateBookEmbeddingsUseCase
    ) -> None:
        self._batch_generate_book_embeddings_use_case = batch_generate_book_embeddings_use_case

    def execute(self) -> EmbeddingRefreshResult:
        try:
            stats = self._batch_generate_book_embeddings_use_case.execute()
        except Exception as exc:  # stage boundary: reported via `failed`, see class docstring
            return EmbeddingRefreshResult(
                requested=0, generated=(), skipped=(), failed=(str(exc),)
            )
        return EmbeddingRefreshResult(
            requested=stats.total_books,
            generated=stats.generated_book_ids,
            skipped=stats.skipped_book_ids,
        )
