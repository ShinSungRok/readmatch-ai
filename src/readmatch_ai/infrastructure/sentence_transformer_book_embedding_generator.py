from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from readmatch_ai.domain.book import Book
from readmatch_ai.domain.book_embedding import BookEmbedding
from readmatch_ai.domain.book_embedding_generator import BookEmbeddingGenerator
from readmatch_ai.domain.book_metadata import BookMetadata
from readmatch_ai.domain.embedding_text import build_embedding_text, embedding_content_hash

# paraphrase-multilingual-MiniLM-L12-v2: a lightweight (~118MB, 384-dim)
# sentence-transformers model trained on 50+ languages, including Korean
# and English -- the two languages readmatch_ai's book catalog spans (see
# Data4Library, the Korean public-library data source). Chosen over the
# earlier English-only all-MiniLM-L6-v2 default so semantic similarity is
# meaningful across the actual catalog, not just its English-language
# subset. Same 384 output dimension, so the existing fixed-width pgvector
# column (migrations/0005) needs no change.
DEFAULT_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_MODEL_VERSION = "1"

# Process-wide cache of loaded SentenceTransformer instances, keyed by model
# name. Loading a model (reading weights from disk, or downloading them the
# first time) is the expensive part of construction; every
# SentenceTransformerBookEmbeddingGenerator built for the same model name
# within one process (e.g. across repeated ApplicationContext.create() calls
# in a batch script or test run) reuses the same in-memory model instead of
# reloading it. Not thread-safe against concurrent first-loads of the *same*
# uncached model name (a benign race: both threads would load and one
# instance's result simply overwrites the other's in the cache) -- acceptable
# for this application's single-process, mostly-sequential usage.
_MODEL_CACHE: dict[str, Any] = {}


class EmbeddingDimensionMismatchError(ValueError):
    """Raised when a model's actual output dimension doesn't match what was expected.

    Catches a misconfigured EMBEDDING_MODEL_NAME (or a model swap) at
    generation time, with a clear cause -- rather than as an opaque
    downstream failure the first time a mismatched vector reaches a
    fixed-width pgvector column.
    """


class SentenceTransformerBookEmbeddingGenerator(BookEmbeddingGenerator):
    """Production BookEmbeddingGenerator backed by a real sentence-transformers model.

    Opt-in via EMBEDDING_GENERATOR_BACKEND=sentence_transformers (see
    config.EmbeddingGeneratorConfig) — DeterministicFakeBookEmbeddingGenerator
    remains the default. The `sentence-transformers` package is an optional
    dependency (pyproject.toml's `embeddings` extra, not installed by
    default); imported lazily here so this module — and the rest of
    Infrastructure — stays importable without it. Never imported/downloaded
    during unit tests: every test for this class injects a fake
    `sentence_transformers` module into `sys.modules` before construction
    (see tests/infrastructure/test_sentence_transformer_book_embedding_generator.py).

    `dimensions` is always derived from the actual encoded vector's length
    (not a separately-reported model property), so a BookEmbedding's
    declared dimensions can never diverge from its vector — the invariant
    BookEmbedding.__post_init__ already enforces before persistence.
    `expected_dimensions`, if given, additionally validates that the
    model's *actual* output matches what the caller expected (see
    EmbeddingDimensionMismatchError) — opt-in, since not every caller has
    (or needs) an expectation to validate against.

    `model_version` (Sprint 48) is a generator-controlled pipeline version,
    independent of `model_name` -- bump it when the embedding text
    construction/normalization changes (see domain.embedding_text) even if
    the underlying model weights don't, so a batch pipeline knows to
    regenerate.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        model_version: str = DEFAULT_MODEL_VERSION,
        expected_dimensions: int | None = None,
    ) -> None:
        self._model_name = model_name
        self._model_version = model_version
        self._expected_dimensions = expected_dimensions
        self._model: Any = self._load_model(model_name)

    @staticmethod
    def _load_model(model_name: str) -> Any:
        cached = _MODEL_CACHE.get(model_name)
        if cached is not None:
            return cached
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name)
        _MODEL_CACHE[model_name] = model
        return model

    def generate(self, book: Book, metadata: BookMetadata | None = None) -> BookEmbedding:
        return self.generate_batch([(book, metadata)])[0]

    def generate_batch(
        self, items: Sequence[tuple[Book, BookMetadata | None]]
    ) -> list[BookEmbedding]:
        if not items:
            return []
        texts = [build_embedding_text(book, metadata) for book, metadata in items]
        # A single vectorized encode() call over every text, instead of one
        # call per book -- the actual batching benefit this Sprint adds;
        # generate() above is just generate_batch() for one item.
        encoded = self._model.encode(texts, normalize_embeddings=True)
        embeddings = []
        for (book, _metadata), text, raw_vector in zip(items, texts, encoded, strict=True):
            vector = tuple(float(component) for component in raw_vector)
            self._validate_dimensions(vector)
            embeddings.append(
                BookEmbedding(
                    book_id=book.id,
                    vector=vector,
                    model_name=self._model_name,
                    model_version=self._model_version,
                    dimensions=len(vector),
                    content_hash=embedding_content_hash(text),
                )
            )
        return embeddings

    def _validate_dimensions(self, vector: tuple[float, ...]) -> None:
        if self._expected_dimensions is not None and len(vector) != self._expected_dimensions:
            raise EmbeddingDimensionMismatchError(
                f"model {self._model_name!r} produced a {len(vector)}-dimensional vector, "
                f"expected {self._expected_dimensions}"
            )
