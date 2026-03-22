# infrastructure/bedrock.py
from langchain_aws import ChatBedrock, BedrockEmbeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from src.core.config import settings
from botocore.config import Config

bedrock_config = Config(
    max_pool_connections=50  
)
def create_chat_bedrock(model_id: str, temperature: float, max_tokens: int, streaming: bool) -> BaseChatModel:
    return ChatBedrock(
        model_id=model_id,
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=bedrock_config,
        streaming=streaming,
        max_tokens=max_tokens,
        temperature=temperature
    )

def create_bedrock_embeddings(model_id: str) -> Embeddings:
    return BedrockEmbeddings(
        model_id=model_id,
        region_name=settings.aws_embedding_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=bedrock_config
    )