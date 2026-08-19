# Entry point — delegates to the app package.
# Run with: python -m uvicorn main:app --reload
from app.main import app  # noqa: F401
