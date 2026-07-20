CREATE EXTENSION IF NOT EXISTS vector;

-- Fixed at 8 to match DeterministicFakeBookEmbeddingGenerator's default
-- dimensions (the only generator wired today). pgvector requires a fixed
-- dimension per column; a future generator with a different dimension
-- (e.g. Sentence Transformers in Sprint 19) will need its own migration.
ALTER TABLE book_embeddings
    ALTER COLUMN vector TYPE vector(8) USING vector::vector(8);

CREATE INDEX IF NOT EXISTS idx_book_embeddings_vector_cosine
    ON book_embeddings USING hnsw (vector vector_cosine_ops);
