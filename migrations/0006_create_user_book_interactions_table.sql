-- No `users` table: a user is identified only by an opaque UUID here (no
-- other User attributes are needed to record and train on implicit
-- interaction signals), so there is nothing else to persist about a user.
CREATE TABLE IF NOT EXISTS user_book_interactions (
    user_id UUID NOT NULL,
    book_id UUID NOT NULL REFERENCES books (id),
    interaction_count INTEGER NOT NULL,
    PRIMARY KEY (user_id, book_id)
);

CREATE INDEX IF NOT EXISTS idx_user_book_interactions_book_id
    ON user_book_interactions (book_id);
