"""
LLM Client - OpenAI-compatible wrapper for DeepSeek, Ollama, OpenAI, etc.
"""

from typing import Optional, Generator
from openai import OpenAI
from loguru import logger

import sys
sys.path.insert(0, str(__file__).rsplit("\\", 3)[0])
from config.settings import settings


class LLMClient:
    """
    Unified LLM client supporting multiple providers:
    - DeepSeek (default)
    - Ollama (local)
    - OpenAI
    - Any OpenAI-compatible API

    Uses lazy initialization for memory efficiency.
    """

    _instance: Optional["LLMClient"] = None
    _client: Optional[OpenAI] = None

    def __new__(cls) -> "LLMClient":
        """Singleton pattern for memory efficiency."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize client configuration (lazy load actual client)."""
        self._provider = settings.llm.provider
        self._base_url = settings.llm.get_base_url()
        self._api_key = settings.llm.get_api_key()
        self._model = settings.llm.model
        self._embedding_model = settings.llm.embedding_model
        self._timeout = settings.llm.timeout
        self._max_tokens = settings.llm.max_tokens
        self._temperature = settings.llm.temperature

    @property
    def client(self) -> OpenAI:
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            logger.info(f"Initializing LLM client: provider={self._provider}, base_url={self._base_url}")

            # Validate API key for non-Ollama providers
            if self._provider != "ollama" and not self._api_key:
                raise ValueError(
                    f"API key required for {self._provider}. "
                    f"Set DEEPSEEK_API_KEY or OPENAI_API_KEY environment variable."
                )

            self._client = OpenAI(
                base_url=self._base_url,
                api_key=self._api_key or "ollama",  # Ollama doesn't need real key
                timeout=self._timeout
            )
        return self._client

    def chat_completion(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> str | Generator[str, None, None]:
        """
        Send chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Override default model
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stream: Whether to stream the response

        Returns:
            Complete response text or generator for streaming
        """
        model = model or self._model
        temperature = temperature if temperature is not None else self._temperature
        max_tokens = max_tokens or self._max_tokens

        logger.debug(f"Chat completion: model={model}, messages={len(messages)}")

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )

            if stream:
                return self._stream_response(response)
            else:
                return response.choices[0].message.content or ""

        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            raise

    def _stream_response(self, response) -> Generator[str, None, None]:
        """Stream response chunks."""
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def embedding(
        self,
        text: str | list[str],
        model: Optional[str] = None
    ) -> list[list[float]]:
        """
        Generate embeddings.

        Note: DeepSeek doesn't provide embedding API.
        For embeddings, we use local sentence-transformers (bge-small-zh).
        This method is kept for API compatibility but uses local model.

        Args:
            text: Single text or list of texts to embed
            model: Override default embedding model

        Returns:
            List of embedding vectors
        """
        # For DeepSeek/OpenAI without embedding support, use local model
        if self._provider in ["deepseek"]:
            return self._local_embedding(text)

        # For Ollama or providers with embedding API
        model = model or self._embedding_model

        if isinstance(text, str):
            text = [text]

        logger.debug(f"Embedding: model={model}, texts={len(text)}")

        try:
            response = self.client.embeddings.create(
                model=model,
                input=text
            )
            return [item.embedding for item in response.data]

        except Exception as e:
            logger.warning(f"API embedding failed, using local model: {e}")
            return self._local_embedding(text)

    def _local_embedding(self, text: str | list[str]) -> list[list[float]]:
        """Generate embeddings using local sentence-transformers model."""
        from sentence_transformers import SentenceTransformer

        if isinstance(text, str):
            text = [text]

        # Use the same model as RAG indexer
        model = SentenceTransformer(settings.rag.embedding_model)
        embeddings = model.encode(text, convert_to_numpy=True)

        return embeddings.tolist()

    def health_check(self) -> bool:
        """Check if LLM service is available."""
        try:
            # Simple request to verify connectivity
            self.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    def analyze_financial_text(
        self,
        text: str,
        extraction_prompt: str
    ) -> str:
        """
        Analyze financial text with structured extraction prompt.

        Args:
            text: Financial document text
            extraction_prompt: Prompt for structured extraction

        Returns:
            Extracted/analyzed content
        """
        system_prompt = """你是一个专业的财务分析助手，专门处理中国城投公司财务报表分析。
请严格按照要求的格式输出，不要添加额外解释。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{extraction_prompt}\n\n文档内容:\n{text[:8000]}"}
        ]

        return self.chat_completion(messages, temperature=0.0)

    def evaluate_rule(
        self,
        rule_description: str,
        financial_context: str,
        evidence: dict
    ) -> dict:
        """
        Use LLM to help evaluate a rule with context.

        Args:
            rule_description: Rule description in Chinese
            financial_context: Relevant financial data context
            evidence: Extracted evidence dict

        Returns:
            Evaluation result dict
        """
        prompt = f"""请根据以下审计规则和财务数据，判断是否存在违规情况。

审计规则:
{rule_description}

财务数据:
{financial_context}

证据:
{evidence}

请回答:
1. 是否违规 (是/否)
2. 简要说明原因
3. 风险评级 (高/中/低)

以JSON格式输出:
{{"violation": true/false, "reason": "...", "risk_level": "..."}}"""

        response = self.chat_completion(
            [{"role": "user", "content": prompt}],
            temperature=0.0
        )

        # Parse JSON response
        import json
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(response[json_start:json_end])
        except json.JSONDecodeError:
            pass

        return {"violation": False, "reason": response, "risk_level": "未知"}


# Backwards compatibility aliases
OllamaClient = LLMClient


def get_llm_client() -> LLMClient:
    """Get singleton LLM client instance."""
    return LLMClient()


# Backwards compatibility
def get_ollama_client() -> LLMClient:
    """Get singleton LLM client instance (backwards compatible)."""
    return LLMClient()
