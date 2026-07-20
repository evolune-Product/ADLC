from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql://sdlc_user:sdlc_pass@localhost:5432/agentic_sdlc"
    redis_url: str = "redis://localhost:6379"

    # LLM
    anthropic_api_key: str = ""

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
    encryption_key: str = "12345678901234567890123456789012"


settings = Settings()
