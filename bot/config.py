from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    bot_token: str
    openai_api_key: str
    database_url: str
    redis_url: str
    yoomoney_wallet: str
    provider_token: str
    
    class Config:
        env_file = ".env"

settings = Settings()

