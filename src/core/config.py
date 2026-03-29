from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # AWS Configuration
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "ap-southeast-3"  
    aws_embedding_region: str = "ap-northeast-1"  
    bedrock_model_id: str = "amazon.nova-lite-v1:0"
    bedrock_embedding_model_id: str

    # redis
    redis_url: str
    redis_ttl : int

    # Logging
    environment : str
    log_level : str

    # LangWatch Configuration
    langwatch_api_key: str = ""
    langwatch_endpoint: str = "https://app.langwatch.ai"
    langwatch_enabled: bool = True

    # history
    max_loaded_history: int

    #page index search
    max_search_iterations: int

    class Config:
        env_file = ".env"

settings = Settings()
