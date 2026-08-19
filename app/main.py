from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.database import create_pool, close_pool
from app.routes import patients, observations, encounters


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    yield
    await close_pool()


app = FastAPI(
    title="FHIR Patient API",
    description="Async FHIR R4B/R5-aligned API — Patient + Observation + Encounter resources",
    lifespan=lifespan,
)

app.include_router(patients.router)
app.include_router(observations.router)
app.include_router(encounters.router)


@app.get("/")
async def root():
    return {"message": "FHIR Patient API", "version": "0.3.0"}
