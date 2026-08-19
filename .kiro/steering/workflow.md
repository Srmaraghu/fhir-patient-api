# Project Workflow Notes

## Git / PR Strategy

- We are pushing directly to `main` for now during active early development.
- **Create a PR when adding a meaningful new feature**, for example:
  - Adding a new FHIR resource (e.g. Encounter, Condition)
  - Adding the HL7 ingestion pipeline
  - Adding data quality / validation layer
  - Adding Airflow or dbt
- PRs are a good habit for the portfolio — recruiters and hiring managers look at PR history on GitHub to assess how someone works.
- Remind the user to create a feature branch before starting the next significant addition:
  `git checkout -b feature/<name>`

## Current Project
- Repo: https://github.com/Srmaraghu/fhir-patient-api
- Stack: FastAPI (async) + asyncpg + PostgreSQL (JSONB) + fhir.resources
- Local dev: DB in Docker via Colima, API runs locally with `python -m uvicorn main:app --reload`
- Start Docker: `colima start` → `docker compose up -d db`
