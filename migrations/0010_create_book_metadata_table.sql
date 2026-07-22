CREATE TABLE book_metadata (
    book_id UUID PRIMARY KEY
        REFERENCES books(id)
        ON DELETE CASCADE,
    publisher TEXT,
    description TEXT,
    cover_url TEXT,
    published_date TEXT
);

CREATE INDEX idx_book_metadata_publisher
    ON book_metadata (publisher);
