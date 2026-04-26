from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    # ───────────────────────── App
    APP_NAME: str = "Petroleum Data API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ───────────────────────── Security
    SECRET_KEY: str = "dev-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ───────────────────────── Database
    DATABASE_URL: str = "postgresql://postgres:lardjan098@localhost:5432/petroleum_mydb"

    # ───────────────────────── Files
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: str = ".las,.csv,.LAS,.CSV"

    # ───────────────────────── Redis (optional)
    REDIS_URL: str = "redis://localhost:6379/0"

    # ───────────────────────── CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ───────────────────────── Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"

    class Config:
        env_file = ".env"

    # ✅ FIX: convert string → list
    @property
    def allowed_origins_list(self):
        return self.ALLOWED_ORIGINS.split(",")


# create settings instance
settings = Settings()

# create folders automatically
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)