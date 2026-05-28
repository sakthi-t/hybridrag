from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import init_db, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db(settings.database_url)
    import app.models  # noqa: F401 — ensure all models are imported
    yield


app = FastAPI(
    title="Hybrid RAG API",
    description="Vector RAG + Graph RAG backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from app.middleware.clerk_auth import get_current_user  # noqa: E402


@app.get("/")
async def root():
    return {"message": "Hybrid RAG API is running"}


@app.post("/api/evaluate/response")
async def evaluate_response(
    body: dict,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    from app.services.evaluation_service import evaluation_service
    result = evaluation_service.evaluate(
        query=body.get("query", ""),
        response=body.get("response", ""),
        context_chunks=body.get("context", body.get("citations")),
    )
    message_id = body.get("message_id")
    if message_id:
        evaluation_service.save_evaluation(
            message_id=message_id,
            scores=result,
            db_session=db,
            latency_ms=body.get("latency_ms"),
        )
    return result


from app.routers import auth, documents, threads, chat, admin, health  # noqa: E402

app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(threads.router, prefix="/api/threads", tags=["Threads"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
