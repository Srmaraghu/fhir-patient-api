-- Bootstrap schema for fhirdb

CREATE TABLE IF NOT EXISTS patients (
    id            TEXT        PRIMARY KEY,          -- FHIR logical id (UUID)
    resource_type TEXT        NOT NULL DEFAULT 'Patient',
    resource      JSONB       NOT NULL,             -- full FHIR Patient resource
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- GIN index for fast JSONB queries e.g. resource->'name'->0->>'family'
CREATE INDEX IF NOT EXISTS idx_patients_resource ON patients USING GIN (resource);

CREATE TABLE IF NOT EXISTS observations (
    id            TEXT        PRIMARY KEY,          -- FHIR logical id (UUID)
    patient_id    TEXT        NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    resource_type TEXT        NOT NULL DEFAULT 'Observation',
    resource      JSONB       NOT NULL,             -- full FHIR Observation resource
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast patient-scoped queries: GET /Observation?patient=<id>
CREATE INDEX IF NOT EXISTS idx_observations_patient_id ON observations (patient_id);
-- GIN index for JSONB queries on observations
CREATE INDEX IF NOT EXISTS idx_observations_resource ON observations USING GIN (resource);
