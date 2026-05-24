"""Application configuration from environment variables."""

import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # Memory backend: 'nams' (hosted) or 'bolt' (self-hosted Neo4j).
    # Auto-corrected at runtime by ``_auto_detect_backend`` when the .env
    # state contradicts the baked default — e.g. user edits .env to swap
    # backends without updating MEMORY_BACKEND. Explicit env wins always.
    memory_backend: str = "bolt"

    # NAMS hosted memory service
    memory_api_key: str = ""
    memory_nams_endpoint: str = "https://memory.neo4jlabs.com/v1"

    # Self-hosted Neo4j (only used when memory_backend == 'bolt').
    # Real values live in .env — never bake credentials into source.
    neo4j_uri: str = ""
    neo4j_username: str = ""
    neo4j_password: str = ""

    # LiteLLM provider strings for memory layer (optional — sane defaults applied)
    memory_llm: str = "anthropic/claude-haiku-4-5-20251001"
    memory_embedding: str = "sentence-transformers/all-MiniLM-L6-v2"

    # LLM provider keys for the agent
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    domain_id: str = "travel-customer-service"
    session_strategy: str = "per_conversation"
    backend_port: int = 8000
    frontend_port: int = 3000









    model_config = {"env_file": (".env", "../.env"), "env_file_encoding": "utf-8", "extra": "ignore"}

    @model_validator(mode="after")
    def _auto_detect_backend(self):
        """Reconcile memory_backend with credentials present in .env.

        Auto-detect only kicks in when the baked backend can't possibly work:
        - ``nams`` with no MEMORY_API_KEY but a populated NEO4J_URI → flip to bolt
        - ``bolt`` with no NEO4J_URI but a populated MEMORY_API_KEY → flip to nams

        If the user explicitly set MEMORY_BACKEND in .env and it disagrees, we
        respect their choice — pydantic-settings already applied env-over-default
        precedence, so by the time we get here ``memory_backend`` IS what they
        asked for. We only auto-correct when the current value is unworkable.
        """
        has_key = bool(self.memory_api_key)
        has_neo4j = bool(self.neo4j_uri)

        if self.memory_backend == "nams" and not has_key and has_neo4j:
            logger.warning(
                "MEMORY_BACKEND=nams but MEMORY_API_KEY is empty while "
                "NEO4J_URI is set — auto-switching to bolt. Set "
                "MEMORY_BACKEND=nams explicitly in .env to override."
            )
            self.memory_backend = "bolt"
        elif self.memory_backend == "bolt" and not has_neo4j and has_key:
            logger.warning(
                "MEMORY_BACKEND=bolt but NEO4J_URI is empty while "
                "MEMORY_API_KEY is set — auto-switching to nams. Set "
                "MEMORY_BACKEND=bolt explicitly in .env to override."
            )
            self.memory_backend = "nams"
        return self


settings = Settings()
