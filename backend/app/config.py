from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_EXPIRES_HOURS: int = 8
    STORAGE_PATH: str = "./storage"
    BACKUP_DRIVE_REMOTE_PATH: str = ""


settings = Settings()
