import uuid
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, status
from fhir.resources.patient import Patient
from fhir.resources.operationoutcome import OperationOutcome

from database import create_pool, close_pool, get_pool


# Lifespan: open / close the asyncpg pool around the app's lifetime
@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    yield
    await close_pool()


app = FastAPI(title="FHIR Patient API", lifespan=lifespan)


# Helpers

def _not_found(patient_id: str) -> HTTPException:
    outcome = OperationOutcome(
        issue=[{
            "severity": "error",
            "code": "not-found",
            "details": {"text": f"Patient/{patient_id} not found"},
        }]
    )
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=outcome.model_dump(),
    )


# Routes

@app.get("/")
async def read_root():
    return {"message": "FHIR Patient API — async edition"}


# CREATE Patient
@app.post("/Patient", status_code=status.HTTP_201_CREATED)
async def create_patient(patient: Patient, response: Response):
    patient_id = str(uuid.uuid4())
    patient.id = patient_id

    resource_json = patient.model_dump_json()

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO patients (id, resource)
            VALUES ($1, $2::jsonb)
            """,
            patient_id,
            resource_json,
        )

    response.headers["Location"] = f"/Patient/{patient_id}"
    return json.loads(resource_json)


#  GET /Patient/{patient_id}
@app.get("/Patient/{patient_id}", status_code=status.HTTP_200_OK)
async def get_patient(patient_id: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT resource FROM patients WHERE id = $1",
            patient_id,
        )

    if not row:
        raise _not_found(patient_id)

    return json.loads(row["resource"])


# UPDATE  
@app.put("/Patient/{patient_id}", status_code=status.HTTP_200_OK)
async def update_patient(patient_id: str, patient: Patient):
    pool = get_pool()

    # confirm the record exists first
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM patients WHERE id = $1",
            patient_id,
        )

    if not exists:
        raise _not_found(patient_id)

    # id in body must match the URL (FHIR convention)
    patient.id = patient_id
    resource_json = patient.model_dump_json()

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE patients
            SET resource   = $2::jsonb,
                updated_at = NOW()
            WHERE id = $1
            """,
            patient_id,
            resource_json,
        )

    return json.loads(resource_json)


# DELETE 
@app.delete("/Patient/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(patient_id: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM patients WHERE id = $1",
            patient_id,
        )

    # asyncpg returns "DELETE N" — check the count
    deleted = int(result.split()[-1])
    if deleted == 0:
        raise _not_found(patient_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
