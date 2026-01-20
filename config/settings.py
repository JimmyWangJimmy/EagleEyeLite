"""
EagleEye Lite - Configuration Settings
Supports both local Ollama and cloud APIs (DeepSeek, OpenAI, etc.)
"""

import os
from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system env vars


class LLMSettings(BaseModel):
    """LLM API configuration - supports Ollama, DeepSeek, OpenAI, etc."""

    # Provider: "ollama", "deepseek", "openai", or custom
    provider: Literal["ollama", "deepseek", "openai", "custom"] = "deepseek"

    # API settings
    base_url: str = "https://api.deepseek.com/v1"  # DeepSeek default
    api_key: Optional[str] = None  # Set via env var DEEPSEEK_API_KEY or OPENAI_API_KEY

    # Model settings
    model: str = "deepseek-chat"  # DeepSeek: deepseek-chat, deepseek-coder
    embedding_model: str = "BAAI/bge-small-zh-v1.5"  # Local embedding model

    # Request settings
    timeout: int = 120
    max_tokens: int = 4096
    temperature: float = 0.1

    def get_api_key(self) -> Optional[str]:
        """Get API key from config or environment variable."""
        if self.api_key:
            return self.api_key

        # Check environment variables based on provider
        env_vars = {
            "deepseek": "DEEPSEEK_API_KEY",
            "openai": "OPENAI_API_KEY",
            "ollama": None,  # Ollama doesn't need API key
        }

        env_var = env_vars.get(self.provider)
        if env_var:
            return os.environ.get(env_var)

        return None

    def get_base_url(self) -> str:
        """Get base URL based on provider."""
        default_urls = {
            "ollama": "http://localhost:11434/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "openai": "https://api.openai.com/v1",
        }

        if self.base_url:
            return self.base_url

        return default_urls.get(self.provider, self.base_url)


# Backwards compatibility alias
OllamaSettings = LLMSettings


class RAGSettings(BaseModel):
    """RAG engine configuration."""
    collection_name: str = "eagleeye_rules"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_dim: int = 512
    similarity_threshold: float = 0.35
    top_k: int = 5
    persist_directory: str = "./chroma_db"


class PDFSettings(BaseModel):
    """PDF parsing configuration."""
    text_density_threshold: int = 100  # chars per page for digital detection
    ocr_languages: list[str] = ["ch_sim", "en"]
    ocr_gpu: bool = False  # CPU mode for Mac Mini
    max_pages: Optional[int] = None
    dpi: int = 200  # For PDF to image conversion


class AuditSettings(BaseModel):
    """Audit workflow configuration."""
    batch_size: int = 1  # Process one rule at a time (memory-efficient)
    max_violations_per_rule: int = 10
    report_format: str = "markdown"  # markdown or json


class Settings(BaseModel):
    """Main application settings."""
    project_root: Path = Path(__file__).parent.parent
    rulebook_path: Path = Path(__file__).parent.parent / "master_rulebook_v3.jsonl"
    output_dir: Path = Path(__file__).parent.parent / "output"
    log_level: str = "INFO"

    llm: LLMSettings = LLMSettings()
    rag: RAGSettings = RAGSettings()
    pdf: PDFSettings = PDFSettings()
    audit: AuditSettings = AuditSettings()

    # Backwards compatibility
    @property
    def ollama(self) -> LLMSettings:
        return self.llm

    def model_post_init(self, __context):
        """Ensure output directory exists."""
        self.output_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
