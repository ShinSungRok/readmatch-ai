-- Sprint 48 (Phase 4): BookEmbedding gains model_version and content_hash,
-- used by the batch embedding pipeline (Sprint 50) to detect which books
-- need regeneration without re-running the model. No embeddings persisted
-- via PostgreSQL exist yet (only the in_memory backend has been used to
-- date), so a transitional default is used only to satisfy NOT NULL for
-- any pre-existing row, then dropped -- new rows must always supply both
-- explicitly.
ALTER TABLE book_embeddings
    ADD COLUMN model_version TEXT NOT NULL DEFAULT 'unknown',
    ADD COLUMN content_hash TEXT NOT NULL DEFAULT 'unknown';

ALTER TABLE book_embeddings
    ALTER COLUMN model_version DROP DEFAULT,
    ALTER COLUMN content_hash DROP DEFAULT;
