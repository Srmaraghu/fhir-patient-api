import uuid
import json

from fastapi import APIRouter, HTTPException, Response, status
from fhir.resources.patient import Patient
from fhir.resources.operationoutcome import OperationOutcome

from app.database import get_pool

router = APIRouter(prefix="/Patient", tags=["Patient"])


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


# CREATE
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_patient(patient: Patient, response: Response):
    patient_id = str(uuid.uuid4())
    patient.id = patient_id
    resource_json = patient.model_dump_json()

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO patients (id, resource_type, resource)
            VALUES ($1, 'Patient', $2::jsonb)
            """,
            patient_id,
            resource_json,
        )

    response.headers["Location"] = f"/Patient/{patient_id}"
    return json.loads(resource_json)


# READ
@router.get("/{patient_id}", status_code=status.HTTP_200_OK)
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


# LIST  GET /Patient?family=Smith
@router.get("", status_code=status.HTTP_200_OK)
async def list_patients(family: str | None = None, given: str | None = None):
    """
    Basic search. Examples:
      GET /Patient?family=Smith
      GET /Patient?given=John
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        if family:
            rows = await conn.fetch(
                """
                SELECT resource FROM patients
                WHERE resource->'name'->0->>'family' ILIKE $1
                """,
                f"%{family}%",
            )
        elif given:
            rows = await conn.fetch(
                """
                SELECT resource FROM patients
                WHERE resource->'name'->0->'given'->0 ILIKE $1
                """,
                f"%{given}%",
            )
        else:
            rows = await conn.fetch("SELECT resource FROM patients")

    return [json.loads(r["resource"]) for r in rows]


# UPDATE (full replace)
@router.put("/{patient_id}", status_code=status.HTTP_200_OK)
async def update_patient(patient_id: str, patient: Patient):
    pool = get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM patients WHERE id = $1", patient_id
        )

    if not exists:
        raise _not_found(patient_id)

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
@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(patient_id: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM patients WHERE id = $1", patient_id
        )

    if int(result.split()[-1]) == 0:
        raise _not_found(patient_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
