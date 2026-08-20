from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "ONIT"

    llm_api_key: str = ""

    nutrient_api_key: str = ""
    nutrient_api_url: str = ""

    serpapi_api_key: str = ""

    doctavian_api_key: str = ""
    doctavian_api_url: str = ""

    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
