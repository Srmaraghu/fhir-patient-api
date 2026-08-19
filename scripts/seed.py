"""
Async seeder — creates realistic synthetic FHIR data via the API.

Usage:
    python scripts/seed.py

Creates:
    - 3 Patients
    - 2 Observations per patient (heart rate + blood pressure)
    - 1 Encounter per patient (office visit)
"""

import asyncio
import httpx

BASE_URL = "http://localhost:8000"

# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

PATIENTS = [
    {
        "resourceType": "Patient",
        "name": [{"family": "Sharma", "given": ["Raj"]}],
        "gender": "male",
        "birthDate": "1985-03-12",
        "telecom": [{"system": "phone", "value": "555-0101", "use": "home"}],
        "address": [{"city": "Boston", "state": "MA", "postalCode": "02115"}],
    },
    {
        "resourceType": "Patient",
        "name": [{"family": "Nepal", "given": ["Emily"]}],
        "gender": "female",
        "birthDate": "1992-07-24",
        "telecom": [{"system": "phone", "value": "555-0202", "use": "home"}],
        "address": [{"city": "Chicago", "state": "IL", "postalCode": "60601"}],
    },
    {
        "resourceType": "Patient",
        "name": [{"family": "Homa", "given": ["Minh"]}],
        "gender": "male",
        "birthDate": "1978-11-05",
        "telecom": [{"system": "phone", "value": "555-0303", "use": "home"}],
        "address": [{"city": "Houston", "state": "TX", "postalCode": "77001"}],
    },
]


def heart_rate_obs(patient_id: str, value: int) -> dict:
    """LOINC 8867-4 — Heart rate"""
    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "8867-4",
                    "display": "Heart rate",
                }
            ]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "valueQuantity": {"value": value, "unit": "beats/min", "system": "http://unitsofmeasure.org", "code": "/min"},
    }


def blood_pressure_obs(patient_id: str, systolic: int, diastolic: int) -> dict:
    """LOINC 55284-4 — Blood pressure"""
    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "55284-4",
                    "display": "Blood pressure systolic and diastolic",
                }
            ]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "component": [
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                "valueQuantity": {"value": systolic, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"},
            },
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                "valueQuantity": {"value": diastolic, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"},
            },
        ],
    }


def office_visit_encounter(patient_id: str) -> dict:
    """
    AMB office visit encounter.

    Note: fhir.resources v8 (FHIR R4B/R5 aligned) changed two fields:
      - Encounter.class  → list of CodeableConcept (was a single Coding in R4)
      - Encounter.period → renamed to actualPeriod
    These shapes are validated and accepted by the server's fhir.resources v8 models.
    """
    return {
        "resourceType": "Encounter",
        "status": "finished",
        "class": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                        "code": "AMB",
                        "display": "ambulatory",
                    }
                ]
            }
        ],
        "type": [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "11429006",
                        "display": "Consultation",
                    }
                ]
            }
        ],
        "subject": {"reference": f"Patient/{patient_id}"},
        "actualPeriod": {"start": "2024-01-15T09:00:00Z", "end": "2024-01-15T09:30:00Z"},
    }


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------

def _check(resp: httpx.Response) -> httpx.Response:
    """Raise with a readable error body on non-2xx."""
    if resp.is_error:
        print(f"  ERROR {resp.status_code}: {resp.text}")
        resp.raise_for_status()
    return resp


async def seed():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # check the API is reachable
        try:
            resp = await client.get("/")
            resp.raise_for_status()
        except Exception:
            print(f"ERROR: Cannot reach API at {BASE_URL}. Is it running?")
            return

        vitals = [
            (72, 120, 80),   # Raj
            (68, 115, 75),   # Emily
            (80, 130, 85),   # Minh
        ]

        for i, patient_data in enumerate(PATIENTS):
            # 1. Create patient
            resp = await client.post("/Patient", json=patient_data)
            _check(resp)
            patient = resp.json()
            pid = patient["id"]
            name = patient["name"][0]["family"]
            print(f"Created Patient/{pid}  ({name})")

            hr, sys_bp, dia_bp = vitals[i]

            # 2. Heart rate observation
            resp = await client.post("/Observation", json=heart_rate_obs(pid, hr))
            _check(resp)
            oid = resp.json()["id"]
            print(f"  Created Observation/{oid}  (heart rate: {hr} bpm)")

            # 3. Blood pressure observation
            resp = await client.post("/Observation", json=blood_pressure_obs(pid, sys_bp, dia_bp))
            _check(resp)
            oid = resp.json()["id"]
            print(f"  Created Observation/{oid}  (BP: {sys_bp}/{dia_bp} mmHg)")

            # 4. Encounter
            resp = await client.post("/Encounter", json=office_visit_encounter(pid))
            _check(resp)
            eid = resp.json()["id"]
            print(f"  Created Encounter/{eid}  (office visit)")

        print("\nSeeding complete.")
        print(f"  Patients:     {len(PATIENTS)}")
        print(f"  Observations: {len(PATIENTS) * 2}")
        print(f"  Encounters:   {len(PATIENTS)}")


if __name__ == "__main__":
    asyncio.run(seed())
