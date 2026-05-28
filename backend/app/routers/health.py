from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.vector_service import vector_service

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "healthy", "version": "0.1.0"}


@router.get("/ready")
async def readiness(db: Session = Depends(get_db)):
    checks = {}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    try:
        vector_service.get_collection_stats()
        checks["chroma"] = "ok"
    except Exception as e:
        checks["chroma"] = f"error: {e}"

    try:
        from app.services.reranking_service import reranking_service
        reranking_service.health_check()
        checks["cohere"] = "ok"
    except Exception as e:
        checks["cohere"] = f"error: {e}"

    status = "ready" if all(v == "ok" for v in checks.values()) else "not_ready"
    return {"status": status, "checks": checks}
