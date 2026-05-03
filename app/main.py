import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.database.session import init_db
from app.routes import auth, users, wells, files, curves, results
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.session import get_db
from app.database.session import engine, Base, init_db
from app.routes.auth import router as auth_router
from fastapi import FastAPI

# ─────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────
logging.basicConfig( 
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Lifespan (startup / shutdown)
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    init_db()
    yield
    logger.info("🛑 Application shutdown")
    
# ─────────────────────────────────────────────
# App factory
# ─────────────────────────────────────────────
Base.metadata.create_all(bind=engine)
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## API de Gestion des Données Pétrolières

Cette API REST permet de gérer :
- 🏗️ **Utilisateurs** avec rôles Admin / Utilisateur
- 🛢️ **Puits pétroliers** (CRUD, recherche, carte)
- 📁 **Fichiers LAS/CSV** avec extraction automatique des courbes
- 📈 **Visualisation** des logs pétrophysiques
- 🔬 **Résultats d'analyse** (porosité, saturation, perméabilité)

### Authentification
Toutes les routes nécessitent un token JWT obtenu via `/auth/login`.
Incluez-le dans le header: `Authorization: Bearer <token>`
    """,
    openapi_tags=[
        {"name": "Authentification", "description": "Inscription, connexion, tokens JWT"},
        {"name": "Utilisateurs", "description": "Gestion des comptes utilisateurs"},
        {"name": "Puits", "description": "CRUD des puits pétroliers"},
        {"name": "Fichiers Pétrophysiques", "description": "Upload et gestion des fichiers LAS/CSV"},
        {"name": "Données de Courbes", "description": "Accès aux données pour visualisation"},
        {"name": "Résultats d'Analyse", "description": "Gestion des résultats pétrophysiques"},
    ],
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)
from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.session import get_db

@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1")).fetchone()
    return {"result": result[0]}
    
@app.get("/make-me-admin")
def make_admin(db: Session = Depends(get_db)):
    from app.models.user import User
    user = db.query(User).filter(User.email == "user12@example.com").first()
    if user:
        user.role = "admin" 
        db.commit()
        return {"message": "You are now an Admin!"}
    return {"error": "User not found"}
# ─────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Exception handlers
# ─────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " → ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Erreur de validation", "errors": errors},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc)
        },
    )


# ─────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────
API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=f"{API_PREFIX}/auth", tags=["Authentification"])
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(files.router, prefix=API_PREFIX)
app.include_router(curves.router, prefix=API_PREFIX)
app.include_router(results.router, prefix=API_PREFIX)
app.include_router(wells.router, prefix="/api/v1")

# ─────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────
@app.get("/health", tags=["Health"], summary="Vérification de l'état de l'API")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/", include_in_schema=False)
def root():
    print(settings.DATABASE_URL)
    return {"message": f"Bienvenue sur {settings.APP_NAME}", "docs": "/docs"}
