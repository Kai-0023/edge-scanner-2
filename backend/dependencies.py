"""Application configuration loaded from the local environment."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings that should stay outside source control."""

    odds_api_key: str | None = Field(default=None, validation_alias="THE_ODDS_API_KEY")
    sportsdata_api_key: str | None = Field(default=None, validation_alias="SPORTS_DATA_IO_API_KEY")
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
