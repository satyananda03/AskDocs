from functools import lru_cache
from langchain_core.embeddings import Embeddings
from typing import List
from src.core.config import settings
from src.infrastructure.bedrock import create_bedrock_embeddings

@lru_cache(maxsize=1)
def get_embeddings(model_id: str = settings.bedrock_embedding_model_id):
    return create_bedrock_embeddings(model_id)

class DummyEmbeddings(Embeddings):
    def __init__(self, size: int = 1):
        self.size = size
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Mengembalikan list of [0.0] sejumlah dokumen
        return [[0.0] * self.size for _ in texts]
    def embed_query(self, text: str) -> List[float]:
        return [0.0] * self.size