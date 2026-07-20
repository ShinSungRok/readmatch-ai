-- 384 matches sentence-transformers/all-MiniLM-L6-v2 (the new
-- SentenceTransformerBookEmbeddingGenerator's default model) and is also
-- adopted as DeterministicFakeBookEmbeddingGenerator's new default
-- dimensions, so storage stays uniform regardless of which provider is
-- configured (pgvector requires one fixed dimension per column).
--
-- No production embeddings exist yet at the old dimension, so the column is
-- dropped and recreated rather than resized in place -- pgvector has no
-- "widen" cast between two different fixed dimensions.
DROP INDEX IF EXISTS idx_book_embeddings_vector_cosine;

ALTER TABLE book_embeddings DROP COLUMN vector;
ALTER TABLE book_embeddings ADD COLUMN vector vector(384) NOT NULL;

CREATE INDEX idx_book_embeddings_vector_cosine
    ON book_embeddings USING hnsw (vector vector_cosine_ops);
