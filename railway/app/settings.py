from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5.6-sol"
    OPENAI_REASONING_EFFORT: str = "low"
    EYE_OF_LOKI_SHARED_SECRET: str = ""
    ALLOWED_ORIGINS: str = (
        "https://eye-of-loki.s1egl0u.chatgpt.site,"
        "http://localhost:3000,http://localhost:4173"
    )
    PAGE_FETCH_TIMEOUT_SECONDS: float = 10.0
    MAX_CONTESTS_PER_RECON: int = 10

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
