"""
conftest.py

Test fixtures for FHIR Patient API.

Strategy: each test gets a fresh asyncpg pool created on its own event loop.
This avoids "attached to a different loop" errors with asyncpg on Python 3.14.

The test database (fhirdb_test) is created once synchronously before tests run.
Each test truncates tables for isolation.
"""

import asyncio
import os
import pytest
import asyncpg
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

os.environ["DB_NAME"] = "fhirdb_test"

from app.main import app
from app import database


def pytest_sessionstart(session):
    """
    Create fhirdb_test and tables once before any tests run.
    Runs synchronously so there's no event loop conflict.
    """
    async def _create_db():
        sys_conn = await asyncpg.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            database="postgres",
            user=os.getenv("DB_USER", "fhiruser"),
            password=os.getenv("DB_PASSWORD", "fhirpassword"),
        )
        await sys_conn.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = 'fhirdb_test' AND pid <> pg_backend_pid()
        """)
        await sys_conn.execute("DROP DATABASE IF EXISTS fhirdb_test")
        await sys_conn.execute("CREATE DATABASE fhirdb_test")
        await sys_conn.close()

        conn = await asyncpg.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            database="fhirdb_test",
            user=os.getenv("DB_USER", "fhiruser"),
            password=os.getenv("DB_PASSWORD", "fhirpassword"),
        )
        init_path = os.path.join(os.path.dirname(__file__), "..", "init.sql")
        with open(init_path) as f:
            await conn.execute(f.read())
        await conn.close()

    asyncio.run(_create_db())


@pytest_asyncio.fixture
async def client():
    """
    Each test gets its own pool (bound to its own event loop) and
    a fresh HTTP client. Tables are truncated before each test.
    """
    # create pool on this test's event loop
    await database.create_pool()

    pool = database.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "TRUNCATE encounters, observations, patients RESTART IDENTITY CASCADE"
        )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    await database.close_pool()


# ── sample FHIR payloads ──────────────────────────────────────────────────────

PATIENT_PAYLOAD = {
    "resourceType": "Patient",
    "name": [{"use": "official", "family": "Smith", "given": ["John", "A"]}],
    "gender": "male",
    "birthDate": "1980-03-15",
}

OBSERVATION_PAYLOAD = {
    "resourceType": "Observation",
    "status": "final",
    "code": {
        "coding": [{
            "system": "http://loinc.org",
            "code": "8480-6",
            "display": "Systolic Blood Pressure",
        }]
    },
    "valueQuantity": {"value": 120, "unit": "mm[Hg]"},
}

ENCOUNTER_PAYLOAD = {
    "resourceType": "Encounter",
    "status": "finished",
    "class": [
        {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                    "code": "IMP",
                    "display": "inpatient encounter",
                }
            ]
        }
    ],
}
