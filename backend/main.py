import sys
from pathlib import Path

# Assure la résolution de 'backend' quel que soit le dossier de travail courant
backend_dir = Path(__file__).resolve().parent
project_root = backend_dir.parent
for p in [str(project_root), str(backend_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.db.pgvector_client import init_db
from backend.routers.documents_router import router as documents_router
from backend.routers.chat_router import router as chat_router

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event to initialize database on startup."""
    logger.info("Démarrage de l'application FastAPI...")
    init_db()
    yield
    logger.info("Arrêt de l'application FastAPI...")


app = FastAPI(
    title="Assistant RAG - Documents Métier",
    description="API RAG complète pour l'indexation et l'interrogation de documents métier avec pgvector.",
    version="1.0.0",
    lifespan=lifespan,
)

# 1. Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permet la connexion depuis le frontend React
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Gestionnaires d'erreurs (400, 404, 500)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle 400 Bad Request on validation errors."""
    error_messages = []
    for err in exc.errors():
        loc = " -> ".join([str(l) for l in err.get("loc", [])])
        msg = err.get("msg", "Entrée invalide")
        error_messages.append(f"{loc}: {msg}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": " | ".join(error_messages)},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle standard HTTP exceptions (400, 404, etc.)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle 500 Internal Server Error."""
    logger.exception(f"Erreur interne inattendue sur {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Erreur interne du serveur : {str(exc)}"},
    )


# 3. Inclusion des routers
app.include_router(documents_router)
app.include_router(chat_router)


@app.get("/health", tags=["system"])
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "rag-assistant-backend"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
