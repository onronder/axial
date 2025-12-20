from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from api.v1.ingest import router as ingest_router
from api.v1.search import router as search_router
from api.v1.chat import router as chat_router
from api.v1.documents import router as documents_router
from core.db import check_connection
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Hybrid RAG SaaS API...")
    is_connected = await check_connection()
    if is_connected:
        logger.info("Database connection checked: ONLINE")
    else:
        logger.warning("Database connection checked: UNREACHABLE (Check credentials or network)")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Hybrid RAG SaaS API...")

app = FastAPI(
    title="Hybrid RAG SaaS API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
origins = [
    "http://localhost",
    "http://localhost:3000",
    "*", # Allow all origins for Railway production ease initially
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(ingest_router, prefix="/api/v1", tags=["ingestion"])
app.include_router(search_router, prefix="/api/v1", tags=["search"])
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
app.include_router(documents_router, prefix="/api/v1", tags=["documents"])
from api.v1.integrations import router as integrations_router
app.include_router(integrations_router, prefix="/api/v1", tags=["integrations"])

# Settings and Team routers
from api.v1.settings import router as settings_router
from api.v1.team import router as team_router
app.include_router(settings_router, prefix="/api/v1", tags=["settings"])
app.include_router(team_router, prefix="/api/v1", tags=["team"])

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.get("/")
def read_root():
    return {"message": "Welcome to Hybrid RAG SaaS API"}
