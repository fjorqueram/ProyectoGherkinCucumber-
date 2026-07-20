from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "ai-qa-gherkin"
    app_env: str = Field(default="dev", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Jira
    jira_base_url: str = Field(default="JIRA_BASE_URL", alias="JIRA_BASE_URL")
    jira_email: str = Field(default="JIRA_EMAIL", alias="JIRA_EMAIL")
    jira_api_token: str = Field(default="JIRA_API_TOKEN", alias="JIRA_API_TOKEN")
    jira_timeout_seconds: int = Field(default=20, alias="JIRA_TIMEOUT_SECONDS")

    # Confluence
    confluence_base_url: str = Field(default="CONFLUENCE_BASE_URL", alias="CONFLUENCE_BASE_URL")
    confluence_email: str = Field(default="CONFLUENCE_EMAIL", alias="CONFLUENCE_EMAIL")
    confluence_api_token: str = Field(default="CONFLUENCE_API_TOKEN", alias="CONFLUENCE_API_TOKEN")
    confluence_timeout_seconds: int = Field(default=20, alias="CONFLUENCE_TIMEOUT_SECONDS")

    # Git Provider (GitHub/GitLab)
    git_provider: str = Field(default="github", alias="GIT_PROVIDER")
    git_api_base_url: str = Field(default="GIT_API_BASE_URL", alias="GIT_API_BASE_URL")
    git_token: str = Field(default="GIT_TOKEN", alias="GIT_TOKEN")
    git_timeout_seconds: int = Field(default=20, alias="GIT_TIMEOUT_SECONDS")
    git_owner: str = Field(default="", alias="GIT_OWNER")
    git_repo: str = Field(default="", alias="GIT_REPO")
    git_base_branch: str = Field(default="develop", alias="GIT_BASE_BRANCH")

    # Xray
    xray_base_url: str = Field(default="https://xray.cloud.getxray.app", alias="XRAY_BASE_URL")
    xray_client_id: str = Field(default="XRAY_CLIENT_ID", alias="XRAY_CLIENT_ID")
    xray_client_secret: str = Field(default="XRAY_CLIENT_SECRET", alias="XRAY_CLIENT_SECRET")
    xray_timeout_seconds: int = Field(default=30, alias="XRAY_TIMEOUT_SECONDS")

    # LLM
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    azure_openai_api_key: str = Field(default="", alias="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_deployment: str = Field(default="", alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = Field(default="2024-10-21", alias="AZURE_OPENAI_API_VERSION")
    github_models_token: str = Field(default="", alias="GITHUB_MODELS_TOKEN")
    github_models_model: str = Field(default="openai/gpt-4.1", alias="GITHUB_MODELS_MODEL")
    github_models_org: str = Field(default="", alias="GITHUB_MODELS_ORG")
    github_models_base_url: str = Field(default="https://models.github.ai", alias="GITHUB_MODELS_BASE_URL")
    ollama_base_url: str = Field(default="http://localhost:11434/v1", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.1", alias="OLLAMA_MODEL")
    lm_studio_base_url: str = Field(default="http://localhost:1234/v1", alias="LM_STUDIO_BASE_URL")
    lm_studio_model: str = Field(default="local-model", alias="LM_STUDIO_MODEL")
    llm_timeout_seconds: int = Field(default=60, alias="LLM_TIMEOUT_SECONDS")
    llm_max_tokens: int = Field(default=5000, alias="LLM_MAX_TOKENS")
    llm_temperature: float = Field(default=0.2, alias="LLM_TEMPERATURE")

    # Retry policy
    retry_max_attempts: int = Field(default=3, alias="RETRY_MAX_ATTEMPTS")
    retry_min_seconds: int = Field(default=1, alias="RETRY_MIN_SECONDS")
    retry_max_seconds: int = Field(default=8, alias="RETRY_MAX_SECONDS")

settings = Settings()
