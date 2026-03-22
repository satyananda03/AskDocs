from langchain_core.language_models import BaseChatModel
from functools import lru_cache
from src.infrastructure.bedrock import create_chat_bedrock


@lru_cache(maxsize=10)
def get_llm(
    model_id: str = "global.amazon.nova-2-lite-v1:0",
    temperature: float = 0,
    max_tokens: int = 500,
    streaming: bool = False
) -> BaseChatModel:
    return create_chat_bedrock(model_id, temperature, max_tokens, streaming)