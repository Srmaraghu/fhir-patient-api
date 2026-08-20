# FHIR Patient API

An async REST API built with FastAPI that serves FHIR R4 resources — Patient, Observation, and Encounter. Designed as the read/API layer of a healthcare data platform, paired with the [hl7-fhir-pipeline](https://github.com/Srmaraghu/hl7-fhir-pipeline) that writes data into the same PostgreSQL database.

## Architecture

```
hl7-fhir-pipeline          fhir-patient-api
(writes data)         →    PostgreSQL    ←    (reads data via REST)
                               │
                         ┌─────┼──────┐
                         │     │      │
                      patients obs  encounters
```

## Features

- FHIR R4 Patient, Observation, Encounter — full CRUD
- FHIR validation using the `fhir.resources` library — invalid payloads are rejected at the request level
- FHIR OperationOutcome error responses — not just plain HTTP errors
- Patient reference validation — Observations and Encounters must reference an existing Patient
- Async PostgreSQL via asyncpg — non-blocking connection pool
- Search support — filter patients by name, observations by patient ID

## Endpoints

### Patient

| Method | Path | Description |
|--------|------|-------------|
| POST | /Patient | Create a new patient |
| GET | /Patient/{id} | Get patient by ID |
| GET | /Patient?family=Smith | Search patients by family name |
| GET | /Patient?given=John | Search patients by given name |
| PUT | /Patient/{id} | Full update |
| DELETE | /Patient/{id} | Delete patient |

### Observation

| Method | Path | Description |
|--------|------|-------------|
| POST | /Observation | Create observation (must reference existing Patient) |
| GET | /Observation/{id} | Get observation by ID |
| GET | /Observation?patient={id} | List all observations for a patient |
| PUT | /Observation/{id} | Full update |
| DELETE | /Observation/{id} | Delete observation |

### Encounter

| Method | Path | Description |
|--------|------|-------------|
| POST | /Encounter | Create encounter (must reference existing Patient) |
| GET | /Encounter/{id} | Get encounter by ID |
| GET | /Encounter?patient={id} | List all encounters for a patient |
| PUT | /Encounter/{id} | Full update |
| DELETE | /Encounter/{id} | Delete encounter |

## Setup

**1. Clone and create virtual environment**

```bash
git clone https://github.com/Srmaraghu/fhir-patient-api.git
cd fhir-patient-api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Start PostgreSQL**

```bash
docker compose up -d
```

**3. Create a `.env` file**

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fhirdb
DB_USER=fhiruser
DB_PASSWORD=fhirpassword
```

**4. Start the API**

```bash
uvicorn app.main:app --reload
```

API is available at http://localhost:8000
Interactive docs at http://localhost:8000/docs

## Example Usage

**Create a Patient**

```bash
curl -X POST http://localhost:8000/Patient \
  -H "Content-Type: application/json" \
  -d '{
    "resourceType": "Patient",
    "name": [{"use": "official", "family": "Smith", "given": ["John"]}],
    "gender": "male",
    "birthDate": "1980-03-15"
  }'
```

**Create an Observation linked to a Patient**

```bash
curl -X POST http://localhost:8000/Observation \
  -H "Content-Type: application/json" \
  -d '{
    "resourceType": "Observation",
    "status": "final",
    "subject": {"reference": "Patient/<patient-id>"},
    "code": {
      "coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic Blood Pressure"}]
    },
    "valueQuantity": {"value": 120, "unit": "mm[Hg]"}
  }'
```

**Search patients by name**

```bash
curl http://localhost:8000/Patient?family=Smith
```

## Tech Stack

| Tool | Purpose |
|------|---------|
| FastAPI | Async web framework |
| asyncpg | Async PostgreSQL driver |
| fhir.resources | FHIR R4 validation and models |
| Pydantic v2 | Data validation |
| PostgreSQL | Storage (JSONB) |
| Docker | Local infrastructure |
| pytest + httpx | Testing |
| GitHub Actions | CI/CD |
