from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql://sdlc_user:sdlc_pass@localhost:5432/agentic_sdlc"
    redis_url: str = "redis://localhost:6379"

    # LLM — Anthropic is the default provider; the rest exist so an org can
    # bring its own model vendor (Forrester's "model agility" criterion) and so
    # self-hosted installs can run fully offline against Ollama.
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    ollama_base_url: str = "http://localhost:11434"
    default_llm_model: str = "claude-sonnet-4-6"

    # Embeddings (codebase memory). Falls back to hashed lexical vectors when unset.
    embedding_api_key: str = ""
    embedding_base_url: str = ""
    embedding_model: str = "text-embedding-3-small"

    # Billing (optional — the platform runs without Stripe configured)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_team: str = ""
    stripe_price_growth: str = ""
    stripe_price_enterprise: str = ""

    # Email (SMTP — works with SES/Postmark/Resend/corporate relay)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False

    # Enterprise / self-hosted
    license_key: str = ""
    deployment_mode: str = "cloud"      # cloud | self_hosted
    audit_retention_days: int = 365
    run_retention_days: int = 0         # 0 = keep forever

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/auth/github/callback"

    # GitLab OAuth
    gitlab_client_id: str = ""
    gitlab_client_secret: str = ""
    gitlab_redirect_uri: str = ""

    # Jira OAuth
    jira_client_id: str = ""
    jira_client_secret: str = ""
    jira_redirect_uri: str = ""

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "agentic-sdlc-skills"
    minio_public_url: str = "http://localhost:9000"

    # Auth
    jwt_secret: str = "change-this-to-a-long-random-secret-key"
    jwt_expiry_hours: int = 24

    # App
    frontend_url: str = "http://localhost:3000"
    # Where this API is reachable from the public internet. Needed because the
    # OIDC redirect URI has to point at the *backend* — the code exchange uses
    # the client secret and must never happen in a browser — and it is the one
    # value that has to be registered with every customer's identity provider,
    # so it cannot be guessed from frontend_url.
    api_base_url: str = "http://localhost:8000"
    encryption_key: str = "12345678901234567890123456789012"


settings = Settings()
