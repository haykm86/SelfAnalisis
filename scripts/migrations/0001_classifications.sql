-- Classifications produced by Batch-API passes over mychatarchive's `chunks` table.
-- One row per (chunk, scheme, label). Multi-label per chunk/scheme is allowed.

CREATE TABLE IF NOT EXISTS classifications (
    classification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id          TEXT    NOT NULL,
    scheme            TEXT    NOT NULL,
    label             TEXT    NOT NULL,
    confidence        REAL,
    model             TEXT    NOT NULL,
    batch_id          TEXT,
    raw               TEXT,
    created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id)
);

CREATE INDEX IF NOT EXISTS idx_classifications_chunk   ON classifications(chunk_id);
CREATE INDEX IF NOT EXISTS idx_classifications_scheme  ON classifications(scheme, label);
CREATE INDEX IF NOT EXISTS idx_classifications_batch   ON classifications(batch_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_classifications_chunk_scheme_label_model
    ON classifications(chunk_id, scheme, label, model);
