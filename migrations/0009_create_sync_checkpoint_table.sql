-- Single-row table: id is fixed to 1 via the CHECK constraint, so there is
-- always at most one checkpoint row, matching InMemorySyncCheckpointRepository's
-- own single-slot semantics.
CREATE TABLE IF NOT EXISTS sync_checkpoint (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    period_end TEXT NOT NULL,
    synced_at TEXT NOT NULL
);
