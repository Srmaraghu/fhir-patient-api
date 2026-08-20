"""
Tests for the /Observation endpoints.
"""

from tests.conftest import PATIENT_PAYLOAD, OBSERVATION_PAYLOAD


async def _create_patient(client) -> str:
    """Helper — create a patient and return its ID."""
    resp = await client.post("/Patient", json=PATIENT_PAYLOAD)
    return resp.json()["id"]


def _obs_with_patient(patient_id: str) -> dict:
    """Return an Observation payload referencing the given patient."""
    return {
        **OBSERVATION_PAYLOAD,
        "subject": {"reference": f"Patient/{patient_id}"},
    }



async def test_create_observation_returns_201(client):
    patient_id = await _create_patient(client)
    resp = await client.post("/Observation", json=_obs_with_patient(patient_id))
    assert resp.status_code == 201



async def test_create_observation_returns_fhir_resource(client):
    patient_id = await _create_patient(client)
    resp = await client.post("/Observation", json=_obs_with_patient(patient_id))
    body = resp.json()
    assert body["resourceType"] == "Observation"
    assert body["status"] == "final"



async def test_create_observation_without_subject_returns_400(client):
    resp = await client.post("/Observation", json=OBSERVATION_PAYLOAD)
    assert resp.status_code == 400



async def test_create_observation_nonexistent_patient_returns_422(client):
    obs = {**OBSERVATION_PAYLOAD, "subject": {"reference": "Patient/nonexistent"}}
    resp = await client.post("/Observation", json=obs)
    assert resp.status_code == 422



async def test_get_observation_returns_200(client):
    patient_id = await _create_patient(client)
    create = await client.post("/Observation", json=_obs_with_patient(patient_id))
    obs_id = create.json()["id"]

    resp = await client.get(f"/Observation/{obs_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == obs_id



async def test_get_observation_not_found_returns_404(client):
    resp = await client.get("/Observation/nonexistent-id")
    assert resp.status_code == 404



async def test_list_observations_by_patient(client):
    patient_id = await _create_patient(client)
    await client.post("/Observation", json=_obs_with_patient(patient_id))
    await client.post("/Observation", json=_obs_with_patient(patient_id))

    resp = await client.get(f"/Observation?patient={patient_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2



async def test_list_observations_empty_returns_empty_list(client):
    resp = await client.get("/Observation")
    assert resp.status_code == 200
    assert resp.json() == []



async def test_delete_observation_returns_204(client):
    patient_id = await _create_patient(client)
    create = await client.post("/Observation", json=_obs_with_patient(patient_id))
    obs_id = create.json()["id"]

    resp = await client.delete(f"/Observation/{obs_id}")
    assert resp.status_code == 204



async def test_delete_observation_not_found_returns_404(client):
    resp = await client.delete("/Observation/nonexistent-id")
    assert resp.status_code == 404
