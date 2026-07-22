-- Sprint 54 (Phase 5): make HNSW index parameters explicit rather than
-- relying on pgvector's implicit defaults.
--
-- m = 16 (max graph connections per node) and ef_construction = 64
-- (candidate list size while building the graph) are pgvector's own
-- defaults -- unchanged in value, but now explicit and documented rather
-- than implicit. Appropriate for this repository's current catalog scale
-- (a small demo dataset; the Data4Library production ingestion pipeline
-- is Phase 6, out of this Phase's scope). A future Sprint importing a
-- much larger catalog should reconsider these: higher m/ef_construction
-- trade slower index builds and more memory for better recall at query
-- time; query-time recall can separately be tuned via the per-session
-- `hnsw.ef_search` parameter (not a build-time/index parameter, so it
-- needs no migration -- see PostgreSQLBookEmbeddingRepository's docstring
-- if a future Sprint wires it up).
--
-- Only the existing cosine-similarity index is recreated here (matching
-- PostgreSQLBookEmbeddingRepository's default `similarity_metric="cosine"`,
-- Sprint 53). The opt-in `"inner_product"` metric's `<#>` queries do not
-- use this index (pgvector requires a separate `vector_ip_ops` index per
-- operator class) and fall back to a sequential scan -- acceptable since
-- no current caller selects that metric; adding a second, currently-unused
-- index would be premature for this Phase's "smallest coherent capability".
DROP INDEX IF EXISTS idx_book_embeddings_vector_cosine;

CREATE INDEX idx_book_embeddings_vector_cosine
    ON book_embeddings USING hnsw (vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
