from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AUTHENTIQ_",
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "AUTHENTIQ"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api"
    secret_key: str = "authentiq-development-secret-change-me-0000000000000000"
    access_token_minutes: int = 45
    refresh_token_days: int = 14
    reset_token_minutes: int = 30
    password_min_length: int = 10

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'authentiq.db').as_posix()}"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173"
    public_app_url: str = "http://localhost:5173"
    api_public_url: str = "http://localhost:8000"

    storage_dir: Path = PROJECT_ROOT / "storage"
    upload_dir: Path = PROJECT_ROOT / "storage" / "uploads"
    evidence_dir: Path = PROJECT_ROOT / "storage" / "evidence"
    ledger_file: Path = PROJECT_ROOT / "storage" / "ledger.jsonl"
    max_file_size_mb: int = 200
    max_chunk_size_mb: int = 8
    allowed_extensions: str = (
        ".png,.jpg,.jpeg,.gif,.webp,.svg,.pdf,.txt,.md,.csv,.json,.doc,.docx,"
        ".xls,.xlsx,.ppt,.pptx,.zip,.mp3,.wav,.flac,.mp4,.mov,.webm,.py,.js,.ts,"
        ".tsx,.jsx,.java,.go,.rs,.c,.cpp,.h,.sol,.circom,.sql,.html,.css,.fig,.sketch"
    )

    ledger_mode: str = "simulation"
    ledger_network: str = "AUTHENTIQ Local Ledger"
    chain_rpc_url: str = ""
    chain_private_key: str = ""
    chain_contract_address: str = ""
    chain_id: int = 80002
    chain_explorer_url: str = "https://amoy.polygonscan.com"

    zkp_mode: str = "sigma"
    zkp_challenge_minutes: int = 10
    zkp_verification_hours: int = 72
    groth16_wasm: str = ""
    groth16_zkey: str = ""
    groth16_vkey: str = ""

    login_rate_limit: int = 8
    login_rate_window_seconds: int = 300
    registration_rate_limit: int = 30
    registration_rate_window_seconds: int = 3600

    demo_mode: bool = True
    seed_demo: bool = False
    access_log: bool = True

    @field_validator("storage_dir", "upload_dir", "evidence_dir", "ledger_file", mode="before")
    @classmethod
    def resolve_path(cls, value):
        path = Path(value)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value):
        if not isinstance(value, str):
            return value
        url = value.strip()
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_extension_list(self) -> list[str]:
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",") if ext.strip()]

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def max_chunk_size_bytes(self) -> int:
        return self.max_chunk_size_mb * 1024 * 1024

    def ensure_directories(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
