import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database.connection import init_db
from app.seed_data.seed_db import seed_database
from app.api.upload import router as upload_router
from app.api.verification import router as verification_router
from app.api.gis import router as gis_router
from app.api.blockchain import router as blockchain_router
from app.api.public import router as public_router
from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.ocr import router as ocr_router
from app.api.integrity import router as integrity_router
from app.api.privacy import router as privacy_router
from app.api.certificate import router as certificate_router
from app.api.orchestration import router as orchestration_router
from app.services.storage_init import ensure_bucket_exists
from app.middleware.security import SecurityHeadersMiddleware, RequestIDMiddleware, RateLimitMiddleware

app = FastAPI(
    title="PlotProof API",
    description="Multi-Vector Forensic Land Title Verification: Document OCR, Cadastral GIS, SHA-256 Blockchain Registry, and ZK Privacy.",
    version="1.0.0"
)

# Apply Security Headers, Request Tracing, and Rate Limiting (Layer 10)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware)

# Enable CORS for Next.js Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.utils.paths import STATIC_DIR, UPLOAD_DIR, CERT_DIR

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Register Routers
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(ocr_router)
app.include_router(integrity_router)
app.include_router(privacy_router)
app.include_router(certificate_router)
app.include_router(orchestration_router)
app.include_router(upload_router)
app.include_router(verification_router)
app.include_router(gis_router)
app.include_router(blockchain_router)
app.include_router(public_router)



@app.on_event("startup")
async def startup_event():
    """
    Auto-initialize database and pre-seed cadastral parcels & sample test deeds.
    """
    init_db()
    seed_database()
    ensure_bucket_exists()


@app.get("/")
def read_root():
    return {
        "system": "PlotProof Land Verification Engine",
        "status": "OPERATIONAL",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "plotproof-backend",
    }

@app.get("/ready")
def readiness_check():
    from app.database.connection import SessionLocal
    from sqlalchemy import text
    db_ok = False
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    finally:
        db.close()

    storage_ok = os.path.exists(str(STATIC_DIR))
    return {
        "status": "ready" if (db_ok and storage_ok) else "not_ready",
        "database": "connected" if db_ok else "disconnected",
        "storage": "accessible" if storage_ok else "inaccessible",
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "services": {
            "document_engine": "online",
            "gis_spatial_engine": "online",
            "trust_blockchain": "online",
            "privacy_zk": "online"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
