import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

_pool: asyncpg.Pool | None = None


async def create_pool() -> asyncpg.Pool:
    global _pool
    _pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "fhirdb"),
        user=os.getenv("DB_USER", "fhiruser"),
        password=os.getenv("DB_PASSWORD", "fhirpassword"),
        min_size=2,
        max_size=10,
    )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialised")
    return _pool
