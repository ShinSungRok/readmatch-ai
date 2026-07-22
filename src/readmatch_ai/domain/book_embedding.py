from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.domain.book import BookId


@dataclass(frozen=True)
class BookEmbedding:
    """A book's semantic embedding vector, recorded independently of the Book aggregate.

    Kept separate from Book (mirrors BookPopularity) since the embedding
    model/version can change independently of catalog metadata.

    `model_version` (Sprint 48) is a generator-controlled pipeline version
    -- bumped when the embedding text construction or normalization logic
    changes, not necessarily when the underlying ML model's weights do --
    distinct from `model_name`, which identifies the model/algorithm
    itself. `content_hash` is `embedding_text.embedding_content_hash()` of
    the canonical text this embedding was generated from. Together,
    `model_version` and `content_hash` let a batch pipeline detect which
    books actually need regeneration (unchanged content + unchanged model
    version can be skipped) without needing to re-run the model to find out.
    """

    book_id: BookId
    vector: tuple[float, ...]
    model_name: str
    model_version: str
    dimensions: int
    content_hash: str

    def __post_init__(self) -> None:
        if not self.model_name.strip():
            raise ValueError("model_name must not be empty")
        if not self.model_version.strip():
            raise ValueError("model_version must not be empty")
        if self.dimensions <= 0:
            raise ValueError("dimensions must be positive")
        if len(self.vector) != self.dimensions:
            raise ValueError(
                f"vector length ({len(self.vector)}) does not match dimensions "
                f"({self.dimensions})"
            )
        if not self.content_hash.strip():
            raise ValueError("content_hash must not be empty")
