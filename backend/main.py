"""
Stub main.py for Story 1.2 Docker infrastructure validation.
Full FastAPI implementation in Story 1.4.
"""
from fastapi import FastAPI
import uvicorn

app = FastAPI(
    title="MétéoScore API",
    description="Weather forecast accuracy comparison platform (Infrastructure stub)",
    version="0.1.0"
)


@app.get("/")
async def root():
    """Health check endpoint for Docker healthcheck."""
    return {
        "status": "healthy",
        "message": "MétéoScore API infrastructure ready (stub)",
        "note": "Full API implementation in Story 1.4"
    }


@app.get("/health")
async def health():
    """Explicit health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    # Run with uvicorn for Docker container
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
