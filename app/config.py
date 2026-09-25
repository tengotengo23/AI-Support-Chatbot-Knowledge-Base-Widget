"""Runtime configuration. Everything is read from environment variables (see .env.example)."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        return int(raw) if raw not in (None, "") else default
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    try:
        return float(raw) if raw not in (None, "") else default
    except ValueError:
        return default


def _load_secret_key(data_dir: Path) -> str:
    """Use SECRET_KEY if given, otherwise generate one and keep it in the data dir
    so that admin sessions survive restarts of a one-command Docker install."""
    key = _env("SECRET_KEY")
    if key:
        return key
    path = data_dir / "secret.key"
    try:
        if path.exists():
            return path.read_text().strip()
        data_dir.mkdir(parents=True, exist_ok=True)
        key = secrets.token_urlsafe(48)
        path.write_text(key)
        os.chmod(path, 0o600)
        return key
    except OSError:
        return secrets.token_urlsafe(48)


@dataclass(frozen=True)
class Settings:
    brand_name: str
    public_url: str
    data_dir: Path
    secret_key: str
    database_url: str

    # LLM
    llm_provider: str
    anthropic_api_key: str
    anthropic_model: str
    openai_api_key: str
    openai_model: str
    openai_base_url: str
    ollama_base_url: str
    ollama_model: str
    embeddings_provider: str
    embeddings_model: str

    # Telegram
    telegram_bot_token: str
    telegram_mode: str
    telegram_webhook_secret: str

    # Accounts & hosting
    signup_enabled: bool
    superadmin_emails: tuple[str, ...]
    billing_enabled: bool
    landing_enabled: bool
    show_badge: bool
    badge_url: str
    demo_widget_key: str
    platform_fee_percent: float
    legal_name: str
    contact_email: str
    legal_updated: str

    # Paddle (hosted billing)
    paddle_env: str
    paddle_client_token: str
    paddle_webhook_secret: str
    paddle_price_starter: str
    paddle_price_pro: str
    paddle_price_business: str

    # Limits
    max_upload_mb: int
    max_crawl_pages: int
    widget_rate_limit_per_minute: int
    allow_private_urls: bool

    @property
    def secure_cookies(self) -> bool:
        return self.public_url.startswith("https://")

    @property
    def llm_enabled(self) -> bool:
        return self.llm_provider in {"anthropic", "openai", "ollama"}


@lru_cache
def get_settings() -> Settings:
    data_dir = Path(_env("DATA_DIR", "./data")).resolve()
    billing = _bool("BILLING_ENABLED", False)
    return Settings(
        brand_name=_env("BRAND_NAME", "Docs2Chat"),
        public_url=_env("PUBLIC_URL", "http://localhost:8000").rstrip("/"),
        data_dir=data_dir,
        secret_key=_load_secret_key(data_dir),
        database_url=_env("DATABASE_URL", f"sqlite:///{data_dir / 'app.db'}"),
        llm_provider=_env("LLM_PROVIDER", "none").lower(),
        anthropic_api_key=_env("ANTHROPIC_API_KEY"),
        anthropic_model=_env("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
        openai_api_key=_env("OPENAI_API_KEY"),
        openai_model=_env("OPENAI_MODEL", "gpt-4.1-mini"),
        openai_base_url=_env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        ollama_base_url=_env("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        ollama_model=_env("OLLAMA_MODEL", "llama3.1"),
        embeddings_provider=_env("EMBEDDINGS_PROVIDER", "none").lower(),
        embeddings_model=_env("EMBEDDINGS_MODEL", ""),
        telegram_bot_token=_env("TELEGRAM_BOT_TOKEN"),
        telegram_mode=_env("TELEGRAM_MODE", "polling").lower(),
        telegram_webhook_secret=_env("TELEGRAM_WEBHOOK_SECRET"),
        signup_enabled=_bool("SIGNUP_ENABLED", True),
        superadmin_emails=tuple(
            e.strip().lower() for e in _env("SUPERADMIN_EMAILS").split(",") if e.strip()
        ),
        billing_enabled=billing,
        landing_enabled=_bool("LANDING_ENABLED", billing),
        show_badge=_bool("SHOW_BADGE", True),
        badge_url=_env(
            "BADGE_URL", "https://github.com/tengotengo23/AI-Support-Chatbot-Knowledge-Base-Widget"
        ),
        demo_widget_key=_env("DEMO_WIDGET_KEY"),
        platform_fee_percent=max(0.0, _float("PLATFORM_FEE_PERCENT", 0.0)),
        legal_name=_env("LEGAL_NAME"),
        contact_email=_env("CONTACT_EMAIL"),
        legal_updated=_env("LEGAL_UPDATED", "2026-09-25"),
        paddle_env=_env("PADDLE_ENV", "sandbox").lower(),
        paddle_client_token=_env("PADDLE_CLIENT_TOKEN"),
        paddle_webhook_secret=_env("PADDLE_WEBHOOK_SECRET"),
        paddle_price_starter=_env("PADDLE_PRICE_STARTER"),
        paddle_price_pro=_env("PADDLE_PRICE_PRO"),
        paddle_price_business=_env("PADDLE_PRICE_BUSINESS"),
        max_upload_mb=_int("MAX_UPLOAD_MB", 20),
        max_crawl_pages=_int("MAX_CRAWL_PAGES", 30),
        widget_rate_limit_per_minute=_int("WIDGET_RATE_LIMIT_PER_MINUTE", 20),
        allow_private_urls=_bool("ALLOW_PRIVATE_URLS", False),
    )
