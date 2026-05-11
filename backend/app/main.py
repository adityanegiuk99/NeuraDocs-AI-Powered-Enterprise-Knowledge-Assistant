"""
FastAPI application entry point.
Configures middleware, lifespan events, and mounts all routes.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware import register_middleware
from app.api.router import api_router
from app.config import settings
from app.db.session import init_db, close_db
from app.utils.logging import setup_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Runs startup logic before yield, cleanup logic after.
    """
    # ── Startup ──
    setup_logging(debug=settings.debug)
    logger = get_logger("startup")
    logger.info("starting_application", app_name=settings.app_name, env=settings.app_env)

    # Ensure data directories exist
    settings.ensure_directories()

    # Initialize database tables
    await init_db()
    logger.info("database_initialized")

    # Initialize embedding model and vector store at startup
    # so they're loaded once, not per-request
    app.state.embedding_service = None
    app.state.vector_store = None

    try:
        if settings.embedding_provider == "huggingface":
            from app.core.embeddings.huggingface import HuggingFaceEmbedding
            app.state.embedding_service = HuggingFaceEmbedding(
                model_name=settings.embedding_model
            )
            logger.info("embedding_model_loaded", model=settings.embedding_model)
    except Exception as e:
        logger.warning("embedding_model_load_failed", error=str(e))

    try:
        from app.core.retrieval.vector_store import FAISSVectorStore
        app.state.vector_store = FAISSVectorStore(
            dimension=settings.embedding_dimension,
            index_path=settings.faiss_index_path,
            metadata_path=settings.faiss_metadata_path,
        )
        logger.info("vector_store_initialized")
    except Exception as e:
        logger.warning("vector_store_init_failed", error=str(e))

    logger.info("startup_complete")

    yield  # ── Application runs here ──

    # ── Shutdown ──
    # Persist FAISS index on shutdown
    if app.state.vector_store:
        try:
            app.state.vector_store.save()
            logger.info("vector_store_saved")
        except Exception as e:
            logger.error("vector_store_save_failed", error=str(e))

    await close_db()
    logger.info("application_shutdown")


app = FastAPI(
    title="AI Knowledge Assistant API",
    description="Production-grade RAG-powered internal knowledge assistant",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# ── CORS Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Custom Middleware (rate limiting, request ID, logging) ──
register_middleware(app, debug=settings.debug)

# ── Mount API Routes ──
app.include_router(api_router)


# ── Root Endpoint ──
@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled",
    }
