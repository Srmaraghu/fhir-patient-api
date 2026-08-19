-- Run once to bootstrap the schema inside the fhirdb database.

CREATE TABLE IF NOT EXISTS patients (
    id          TEXT        PRIMARY KEY,               -- FHIR logical id (UUID)
    resource    JSONB       NOT NULL,                  -- full FHIR Patient resource
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index the JSONB column so searches on common FHIR fields are fast.
CREATE INDEX IF NOT EXISTS idx_patients_resource ON patients USING GIN (resource);
