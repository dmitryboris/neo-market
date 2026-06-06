from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "b2b"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    ALLOWED_EXTENSIONS: set = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    MAX_FILE_SIZE: int = 5 * 1024 * 1024   # 5 MB
    UPLOAD_DIR: str = "uploads"

    MODERATION_URL: str = "https://moderation.example.com"
    B2C_URL: str = "https://b2c.example.com"
    B2B_TO_MOD_KEY: str = "change-me"
    B2B_TO_B2C_KEY: str = "change-me"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def sync_database_url(self) -> str:
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
