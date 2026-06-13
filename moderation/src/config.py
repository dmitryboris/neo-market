from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MOD_DB_USER: str = "postgres"
    MOD_DB_PASSWORD: str = "postgres"
    MOD_DB_NAME: str = "moderation"
    MOD_DB_HOST: str = "localhost"
    MOD_DB_PORT: int = 5432

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    ALLOWED_EXTENSIONS: set = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    MAX_FILE_SIZE: int = 5 * 1024 * 1024   # 5 MB
    UPLOAD_DIR: str = "uploads"

    B2C_URL: str = "https://b2c.example.com"
    B2B_URL: str = "https://b2b.example.com"
    MOD_TO_B2C_KEY: str = "change-me"
    MOD_TO_B2B_KEY: str = "change-me"
    B2C_TO_MOD_KEY: str = "change-me"
    B2B_TO_MOD_KEY: str = "change-me"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.MOD_DB_USER}:{self.MOD_DB_PASSWORD}@{self.MOD_DB_HOST}:{self.MOD_DB_PORT}/{self.MOD_DB_NAME}"

    @property
    def sync_database_url(self) -> str:
        return f"postgresql+psycopg2://{self.MOD_DB_USER}:{self.MOD_DB_PASSWORD}@{self.MOD_DB_HOST}:{self.MOD_DB_PORT}/{self.MOD_DB_NAME}"


settings = Settings()
