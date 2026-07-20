CREATE TABLE IF NOT EXISTS book_embeddings (
    book_id UUID PRIMARY KEY REFERENCES books (id),
    vector DOUBLE PRECISION[] NOT NULL,
    model_name TEXT NOT NULL,
    dimensions INTEGER NOT NULL
);
