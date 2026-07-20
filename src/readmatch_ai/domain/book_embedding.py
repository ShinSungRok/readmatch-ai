from __future__ import annotations

from dataclasses import dataclass

from readmatch_ai.domain.book import BookId


@dataclass(frozen=True)
class BookEmbedding:
    """A book's semantic embedding vector, recorded independently of the Book aggregate.

    Kept separate from Book (mirrors BookPopularity) since the embedding
    model/version can change independently of catalog metadata.
    """

    book_id: BookId
    vector: tuple[float, ...]
    model_name: str
    dimensions: int

    def __post_init__(self) -> None:
        if not self.model_name.strip():
            raise ValueError("model_name must not be empty")
        if self.dimensions <= 0:
            raise ValueError("dimensions must be positive")
        if len(self.vector) != self.dimensions:
            raise ValueError(
                f"vector length ({len(self.vector)}) does not match dimensions "
                f"({self.dimensions})"
            )
