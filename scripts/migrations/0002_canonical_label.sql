-- Add canonical_label column to classifications for topic normalization.
-- Original `label` stays untouched (source of truth from the model).
-- `canonical_label` holds the normalized form after the mapping pass.
-- NULL means "not yet normalized" — queries that want normalized values
-- should COALESCE(canonical_label, label).

ALTER TABLE classifications ADD COLUMN canonical_label TEXT;

CREATE INDEX IF NOT EXISTS idx_classifications_canonical_label
  ON classifications(scheme, canonical_label);
