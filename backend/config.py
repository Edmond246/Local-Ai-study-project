from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    MODEL_NAME: str = "qwen2.5:3b"
    
    CHUNK_SIZE: int = 3000
    OVERLAP: int = 200
    MAX_CHUNKS: int = 10
    
    CARD_TARGET_MIN: int = 3
    CARD_TARGET_MAX: int = 15
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()