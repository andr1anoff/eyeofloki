from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_THINKING_LEVEL: str = "medium"
    TAVILY_API_KEY: str = ""
    EYE_OF_LOKI_SHARED_SECRET: str = ""
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:4173"
    PAGE_FETCH_TIMEOUT_SECONDS: float = 10.0
    MAX_CONTESTS_PER_RECON: int = 10
    SEARCH_RESULTS_PER_CONTEST: int = 4

    # One validator pass. Adaptive discovery may run several deliberately
    # different passes, but each pass stays bounded for latency and API cost.
    DISCOVERY_QUERIES_PER_RUN: int = 8
    DISCOVERY_RESULTS_PER_QUERY: int = 8
    MAX_DISCOVERY_CANDIDATES: int = 24
    DISCOVERY_MIN_SCORE: int = 40
    DISCOVERY_MIN_CHANCE_PPM: int = 100
    DISCOVERY_MAX_HUB_SCORE: int = 45
    DISCOVERY_TIME_RANGE: str = "month"
    DISCOVERY_MAX_HARVESTED: int = 10
    DISCOVERY_BLOCKED_HOSTS: str = ""

    # Search-controller settings. The first pass is precise; later passes widen
    # recency and ranking thresholds only when the queue is still under-filled.
    ADAPTIVE_TARGET_RESULTS: int = 8
    ADAPTIVE_MAX_PASSES: int = 3
    ADAPTIVE_QUERIES_PER_PASS: int = 6

    @property
    def blocked_hosts(self) -> set[str]:
        return {
            host.strip().lower().removeprefix("www.")
            for host in self.DISCOVERY_BLOCKED_HOSTS.split(",")
            if host.strip()
        }

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
