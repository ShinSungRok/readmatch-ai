CREATE TABLE IF NOT EXISTS book_popularity (
    book_id UUID PRIMARY KEY REFERENCES books (id),
    loan_count INTEGER NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_book_popularity_loan_count
    ON book_popularity (loan_count DESC);
