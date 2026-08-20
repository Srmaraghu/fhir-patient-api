from tests.conftest import PATIENT_PAYLOAD



async def test_create_patient_returns_201(client):
    resp = await client.post("/Patient", json=PATIENT_PAYLOAD)
    assert resp.status_code == 201



async def test_create_patient_returns_location_header(client):
    resp = await client.post("/Patient", json=PATIENT_PAYLOAD)
    assert "location" in resp.headers
    assert resp.headers["location"].startswith("/Patient/")



async def test_create_patient_returns_fhir_resource(client):
    resp = await client.post("/Patient", json=PATIENT_PAYLOAD)
    body = resp.json()
    assert body["resourceType"] == "Patient"
    assert body["name"][0]["family"] == "Smith"
    assert body["gender"] == "male"



async def test_get_patient_returns_200(client):
    create = await client.post("/Patient", json=PATIENT_PAYLOAD)
    patient_id = create.json()["id"]

    resp = await client.get(f"/Patient/{patient_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == patient_id



async def test_get_patient_not_found_returns_404(client):
    resp = await client.get("/Patient/nonexistent-id")
    assert resp.status_code == 404



async def test_get_patient_not_found_returns_operation_outcome(client):
    resp = await client.get("/Patient/nonexistent-id")
    body = resp.json()
    assert "issue" in body["detail"]



async def test_list_patients_returns_all(client):
    await client.post("/Patient", json=PATIENT_PAYLOAD)
    await client.post("/Patient", json=PATIENT_PAYLOAD)

    resp = await client.get("/Patient")
    assert resp.status_code == 200
    assert len(resp.json()) == 2



async def test_list_patients_empty_returns_empty_list(client):
    resp = await client.get("/Patient")
    assert resp.status_code == 200
    assert resp.json() == []



async def test_search_patient_by_family_name(client):
    await client.post("/Patient", json=PATIENT_PAYLOAD)
    resp = await client.get("/Patient?family=Smith")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"][0]["family"] == "Smith"



async def test_search_patient_by_family_name_no_match(client):
    await client.post("/Patient", json=PATIENT_PAYLOAD)
    resp = await client.get("/Patient?family=Jones")
    assert resp.status_code == 200
    assert resp.json() == []



async def test_update_patient_returns_200(client):
    create = await client.post("/Patient", json=PATIENT_PAYLOAD)
    patient_id = create.json()["id"]

    updated = {**PATIENT_PAYLOAD, "gender": "female"}
    resp = await client.put(f"/Patient/{patient_id}", json=updated)
    assert resp.status_code == 200
    assert resp.json()["gender"] == "female"



async def test_update_patient_not_found_returns_404(client):
    resp = await client.put("/Patient/nonexistent-id", json=PATIENT_PAYLOAD)
    assert resp.status_code == 404



async def test_delete_patient_returns_204(client):
    create = await client.post("/Patient", json=PATIENT_PAYLOAD)
    patient_id = create.json()["id"]

    resp = await client.delete(f"/Patient/{patient_id}")
    assert resp.status_code == 204



async def test_delete_patient_not_found_returns_404(client):
    resp = await client.delete("/Patient/nonexistent-id")
    assert resp.status_code == 404



async def test_delete_patient_removes_from_db(client):
    create = await client.post("/Patient", json=PATIENT_PAYLOAD)
    patient_id = create.json()["id"]

    await client.delete(f"/Patient/{patient_id}")
    resp = await client.get(f"/Patient/{patient_id}")
    assert resp.status_code == 404
