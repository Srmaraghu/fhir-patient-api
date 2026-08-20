"""
Tests for the /Encounter endpoints.
"""

from tests.conftest import PATIENT_PAYLOAD, ENCOUNTER_PAYLOAD


async def _create_patient(client) -> str:
    resp = await client.post("/Patient", json=PATIENT_PAYLOAD)
    return resp.json()["id"]


def _enc_with_patient(patient_id: str) -> dict:
    return {
        **ENCOUNTER_PAYLOAD,
        "subject": {"reference": f"Patient/{patient_id}"},
    }



async def test_create_encounter_returns_201(client):
    patient_id = await _create_patient(client)
    resp = await client.post("/Encounter", json=_enc_with_patient(patient_id))
    assert resp.status_code == 201



async def test_create_encounter_returns_fhir_resource(client):
    patient_id = await _create_patient(client)
    resp = await client.post("/Encounter", json=_enc_with_patient(patient_id))
    body = resp.json()
    assert body["resourceType"] == "Encounter"
    assert body["status"] == "finished"



async def test_create_encounter_without_subject_returns_400(client):
    resp = await client.post("/Encounter", json=ENCOUNTER_PAYLOAD)
    assert resp.status_code == 400



async def test_create_encounter_nonexistent_patient_returns_422(client):
    enc = {**ENCOUNTER_PAYLOAD, "subject": {"reference": "Patient/nonexistent"}}
    resp = await client.post("/Encounter", json=enc)
    assert resp.status_code == 422



async def test_get_encounter_returns_200(client):
    patient_id = await _create_patient(client)
    create = await client.post("/Encounter", json=_enc_with_patient(patient_id))
    enc_id = create.json()["id"]

    resp = await client.get(f"/Encounter/{enc_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == enc_id



async def test_get_encounter_not_found_returns_404(client):
    resp = await client.get("/Encounter/nonexistent-id")
    assert resp.status_code == 404



async def test_list_encounters_by_patient(client):
    patient_id = await _create_patient(client)
    await client.post("/Encounter", json=_enc_with_patient(patient_id))
    await client.post("/Encounter", json=_enc_with_patient(patient_id))

    resp = await client.get(f"/Encounter?patient={patient_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2



async def test_list_encounters_empty_returns_empty_list(client):
    resp = await client.get("/Encounter")
    assert resp.status_code == 200
    assert resp.json() == []



async def test_delete_encounter_returns_204(client):
    patient_id = await _create_patient(client)
    create = await client.post("/Encounter", json=_enc_with_patient(patient_id))
    enc_id = create.json()["id"]

    resp = await client.delete(f"/Encounter/{enc_id}")
    assert resp.status_code == 204



async def test_delete_encounter_not_found_returns_404(client):
    resp = await client.delete("/Encounter/nonexistent-id")
    assert resp.status_code == 404
