import uuid
import json

from fastapi import APIRouter, HTTPException, Response, status
from fhir.resources.observation import Observation
from fhir.resources.operationoutcome import OperationOutcome

from app.database import get_pool

router = APIRouter(prefix="/Observation", tags=["Observation"])


def _not_found(obs_id: str) -> HTTPException:
    outcome = OperationOutcome(
        issue=[{
            "severity": "error",
            "code": "not-found",
            "details": {"text": f"Observation/{obs_id} not found"},
        }]
    )
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=outcome.model_dump(),
    )


def _bad_request(msg: str) -> HTTPException:
    outcome = OperationOutcome(
        issue=[{
            "severity": "error",
            "code": "invalid",
            "details": {"text": msg},
        }]
    )
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=outcome.model_dump(),
    )


def _extract_patient_id(observation: Observation) -> str | None:
    """Pull the patient id out of subject.reference e.g. 'Patient/abc-123'."""
    if not observation.subject or not observation.subject.reference:
        return None
    ref = observation.subject.reference
    if ref.startswith("Patient/"):
        return ref.split("/", 1)[1]
    return None


# CREATE
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_observation(observation: Observation, response: Response):
    patient_id = _extract_patient_id(observation)
    if not patient_id:
        raise _bad_request(
            "Observation.subject.reference must be set to 'Patient/<id>'"
        )

    pool = get_pool()
    async with pool.acquire() as conn:
        # verify the referenced patient exists
        patient_exists = await conn.fetchval(
            "SELECT 1 FROM patients WHERE id = $1", patient_id
        )
        if not patient_exists:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Referenced Patient/{patient_id} does not exist",
            )

        obs_id = str(uuid.uuid4())
        observation.id = obs_id
        resource_json = observation.model_dump_json()

        await conn.execute(
            """
            INSERT INTO observations (id, patient_id, resource_type, resource)
            VALUES ($1, $2, 'Observation', $3::jsonb)
            """,
            obs_id,
            patient_id,
            resource_json,
        )

    response.headers["Location"] = f"/Observation/{obs_id}"
    return json.loads(resource_json)


# READ
@router.get("/{obs_id}", status_code=status.HTTP_200_OK)
async def get_observation(obs_id: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT resource FROM observations WHERE id = $1", obs_id
        )

    if not row:
        raise _not_found(obs_id)

    return json.loads(row["resource"])


# LIST by patient  GET /Observation?patient=<id>
@router.get("", status_code=status.HTTP_200_OK)
async def list_observations(patient: str | None = None):
    """
    GET /Observation             → all observations
    GET /Observation?patient=id  → all observations for a patient
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        if patient:
            rows = await conn.fetch(
                "SELECT resource FROM observations WHERE patient_id = $1",
                patient,
            )
        else:
            rows = await conn.fetch("SELECT resource FROM observations")

    return [json.loads(r["resource"]) for r in rows]


# UPDATE (full replace)
@router.put("/{obs_id}", status_code=status.HTTP_200_OK)
async def update_observation(obs_id: str, observation: Observation):
    # validate subject reference and patient existence
    patient_id = _extract_patient_id(observation)
    if not patient_id:
        raise _bad_request("Observation.subject.reference must be set to 'Patient/<id>'")

    pool = get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM observations WHERE id = $1", obs_id
        )

    if not exists:
        raise _not_found(obs_id)

    async with pool.acquire() as conn:
        patient_exists = await conn.fetchval(
            "SELECT 1 FROM patients WHERE id = $1", patient_id
        )
    if not patient_exists:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Referenced Patient/{patient_id} does not exist",
        )

    observation.id = obs_id
    resource_json = observation.model_dump_json()

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE observations
            SET resource   = $2::jsonb,
                patient_id = $3,
                updated_at = NOW()
            WHERE id = $1
            """,
            obs_id,
            resource_json,
            patient_id,
        )

    return json.loads(resource_json)


# DELETE
@router.delete("/{obs_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_observation(obs_id: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM observations WHERE id = $1", obs_id
        )

    if int(result.split()[-1]) == 0:
        raise _not_found(obs_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
