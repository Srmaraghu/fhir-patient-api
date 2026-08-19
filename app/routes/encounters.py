import uuid
import json

from fastapi import APIRouter, HTTPException, Response, status
from fhir.resources.encounter import Encounter
from fhir.resources.operationoutcome import OperationOutcome

from app.database import get_pool

router = APIRouter(prefix="/Encounter", tags=["Encounter"])


def _not_found(enc_id: str) -> HTTPException:
    outcome = OperationOutcome(
        issue=[{
            "severity": "error",
            "code": "not-found",
            "details": {"text": f"Encounter/{enc_id} not found"},
        }]
    )
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=outcome.model_dump(),
    )


def _extract_patient_id(encounter: Encounter) -> str | None:
    """Pull patient id from subject.reference e.g. 'Patient/abc-123'."""
    if not encounter.subject or not encounter.subject.reference:
        return None
    ref = encounter.subject.reference
    if ref.startswith("Patient/"):
        return ref.split("/", 1)[1]
    return None


# CREATE
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_encounter(encounter: Encounter, response: Response):
    patient_id = _extract_patient_id(encounter)
    if not patient_id:
        outcome = OperationOutcome(
            issue=[{
                "severity": "error",
                "code": "invalid",
                "details": {"text": "Encounter.subject.reference must be set to 'Patient/<id>'"},
            }]
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=outcome.model_dump(),
        )

    pool = get_pool()
    async with pool.acquire() as conn:
        patient_exists = await conn.fetchval(
            "SELECT 1 FROM patients WHERE id = $1", patient_id
        )
        if not patient_exists:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Referenced Patient/{patient_id} does not exist",
            )

        enc_id = str(uuid.uuid4())
        encounter.id = enc_id
        resource_json = encounter.model_dump_json()

        await conn.execute(
            """
            INSERT INTO encounters (id, patient_id, resource_type, resource)
            VALUES ($1, $2, 'Encounter', $3::jsonb)
            """,
            enc_id,
            patient_id,
            resource_json,
        )

    response.headers["Location"] = f"/Encounter/{enc_id}"
    return json.loads(resource_json)


# READ
@router.get("/{enc_id}", status_code=status.HTTP_200_OK)
async def get_encounter(enc_id: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT resource FROM encounters WHERE id = $1", enc_id
        )

    if not row:
        raise _not_found(enc_id)

    return json.loads(row["resource"])


# LIST  GET /Encounter?patient=<id>
@router.get("", status_code=status.HTTP_200_OK)
async def list_encounters(patient: str | None = None):
    """
    GET /Encounter             → all encounters
    GET /Encounter?patient=id  → all encounters for a patient
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        if patient:
            rows = await conn.fetch(
                "SELECT resource FROM encounters WHERE patient_id = $1", patient
            )
        else:
            rows = await conn.fetch("SELECT resource FROM encounters")

    return [json.loads(r["resource"]) for r in rows]


# UPDATE (full replace)
@router.put("/{enc_id}", status_code=status.HTTP_200_OK)
async def update_encounter(enc_id: str, encounter: Encounter):
    # validate subject reference
    patient_id = _extract_patient_id(encounter)
    if not patient_id:
        outcome = OperationOutcome(
            issue=[{
                "severity": "error",
                "code": "invalid",
                "details": {"text": "Encounter.subject.reference must be set to 'Patient/<id>'"},
            }]
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=outcome.model_dump(),
        )

    pool = get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM encounters WHERE id = $1", enc_id
        )

    if not exists:
        raise _not_found(enc_id)

    # verify the referenced patient exists
    async with pool.acquire() as conn:
        patient_exists = await conn.fetchval(
            "SELECT 1 FROM patients WHERE id = $1", patient_id
        )
    if not patient_exists:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Referenced Patient/{patient_id} does not exist",
        )

    encounter.id = enc_id
    resource_json = encounter.model_dump_json()

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE encounters
            SET resource   = $2::jsonb,
                patient_id = $3,
                updated_at = NOW()
            WHERE id = $1
            """,
            enc_id,
            resource_json,
            patient_id,
        )

    return json.loads(resource_json)


# DELETE
@router.delete("/{enc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_encounter(enc_id: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM encounters WHERE id = $1", enc_id
        )

    if int(result.split()[-1]) == 0:
        raise _not_found(enc_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
